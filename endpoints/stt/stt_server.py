from sanic import Sanic
from sanic.response import json
from sanic.log import logger

import os
import urllib.request
import datetime
import asyncio
from asyncio.subprocess import PIPE, STDOUT

import sox
import base64

UPLOAD_DIR = "./uploads"
API_NAME = "stt_server"

app = Sanic(API_NAME)
app.config.PROXIES_COUNT = 1
app.config.KEEP_ALIVE_TIMEOUT = 10

job_states = {}
job_id = 1

def get_next_job_id():
    global job_id

    job_id += 1
    return job_id

@app.route("/stt_file", methods=["POST",])
async def stt_post_file(request):

    # Ensure a file was sent
    upload_file = request.files.get('file_names')
    if not upload_file:
        return json({"success": False, "error":"no file"})

    # Clean up the filename in case it creates security risks
#    filename = secure_filename(upload_file.name)

    # Ensure the file is a valid type and size, and if so
    # write the file to disk and redirect back to main
#    if not valid_file_type(upload_file.name, upload_file.type):
#        return redirect('/?error=invalid_file_type')
#    elif not valid_file_size(upload_file.body):
#        return redirect('/?error=invalid_file_size')
#    else:
    file_path = f"{UPLOAD_DIR}/{str(datetime.datetime.now())}.ogg"
    await write_file(file_path, upload_file.body)
    return json({"success": True})

@app.route("/stt", methods=["POST",])
async def stt_post_json(request):
    req_json = request.json
    confg = req_json['config']
    uri = req_json['audio']['uri']
    audio_clip = urllib.request.urlopen(uri).read()

    filename = f"{UPLOAD_DIR}/rec-{str(datetime.datetime.now())}".replace(":","").replace(" ","_")
    ogg_filename = filename + ".ogg"
    ogg_file = open(ogg_filename, 'wb')
    ogg_file.write(audio_clip)
    ogg_file.close()

    wav_filename = filename + ".wav"

 #   convert_cmd = f"opusdec {ogg_filename} {wav_filename}"
    convert_cmd = f"ffmpeg -i {ogg_filename} {wav_filename}"

    logger.info('Start converting .ogg to .wavs')
    process = await asyncio.create_subprocess_shell(convert_cmd, stdin = PIPE, stdout = PIPE, stderr = STDOUT)

    # Wait for the subprocess to finish
    stdout, stderr = await process.communicate()

    if os.path.exists(wav_filename):
        logger.info('.ogg conversion finished')
    else:
        logger.error('.ogg conversion failed!')
        return json({"success": False, "error":"could not decode audio"})

    try:
        duration = sox.file_info.duration(wav_filename)
        sample_rate = sox.file_info.sample_rate(wav_filename)
    except:
        logger.error("Sox error reading file: " + wav_filename)
        return json({"success": False, "error":"no audio data"})

    logger.info(f"sample rate: {sample_rate}  duration: {duration}")

    wav16k_filename = filename + "_.wav"

    tfm = sox.Transformer()
    tfm.convert(16000)
    tfm.build(wav_filename, wav16k_filename)

    # --- run deepsepech as CMD
    #speech_cmd = f"cd /home/deploy/DeepSpeechX; python3 DeepSpeech.py --alphabet_config_path ./data_de/alphabet.txt --lm_binary_path ./data_de/lm2/lm.binary --lm_trie_path ./data_de/lm2/trie --checkpoint_dir ./checkpoints/de_v3_3072_lrn0001 --n_hidden 3072 --one_shot_infer {os.path.abspath(wav16k_filename)}"
    #process = await asyncio.create_subprocess_shell(speech_cmd, stdin = PIPE, stdout = PIPE, stderr = STDOUT)
    #stdout, stderr = await process.communicate()

    #--- put into the worker queue and await response_json
    logger.info("putting a job into the queue ... ")
    job_id = get_next_job_id()
    job_future = asyncio.Future(loop=app.loop)
    job_states[job_id] = job_future
    job_data = {}
    job_data['id'] = job_id
    with open(wav16k_filename, "rb") as audio_file:
      job_data['wav'] = base64.b64encode(audio_file.read())

    await queue.put(job_data)

    result = await job_future
    logger.info("... got job result: " + str(result))
    response = {"success": True}
    response['text'] = result['text']
    response['logits'] = result['logits']
    response['decoder_scores'] = result['decoder_scores']
    return json(response)


@app.route("/worker_job_request", methods=["POST",])
async def worker_job_request_json(request):
    global job_states

    req_json = request.json
    print(str(req_json))

    logger.info("waiting on queue for a job ... ")
    job_data = await queue.get()
    job_id = job_data['id']
    wav16k_filename = job_data['wav']

    logger.info(f"job_request {job_id}")
    queue.task_done()
    job_cmd = {"cmd": "job"}
    job_cmd['job_id'] = job_id
    job_cmd['wav'] = wav16k_filename
    return json(job_cmd)

@app.route("/worker_job_result", methods=["POST",])
async def worker_job_result_json(request):
    global job_states

    req_json = request.json
    print(str(req_json))

    job_id = int(req_json['job_id'])
    logger.info(f"job_result {job_id}")
    job_result = req_json
    job_states[job_id].set_result(job_result)
    logger.info("... processed queue job")
    job_cmd = {"cmd": "ok"}
    return json(job_cmd)


@app.route("/job_trigger", methods=["GET",])
async def worker_connection_json(request):
    global job_states

    logger.info("putting a job into the queue ... ")
    job_id = get_next_job_id()
    job_future = asyncio.Future(loop=app.loop)
    job_states[job_id] = job_future

    job_data = {}
    job_data['id'] = job_id
    await queue.put(job_data)

    result = await job_future
    logger.info("... got job result: " + str(result))
    response = {"success": True}
    response['result'] = str(result)
    return json(response)


@app.listener('after_server_start')
def create_task_queue(app, loop):
    global queue
    logger.info("--- creating queue")
    queue = asyncio.Queue(loop=loop)

app.static('/audiorecorder', './audiorecorder')


if __name__ == "__main__":

   # Create upload folder if doesn't exist
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)

    app.run(host="0.0.0.0", port=7777)
