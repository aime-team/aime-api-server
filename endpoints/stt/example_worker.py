import aiohttp
import asyncio
import json
import base64

JOB_SERVER = 'http://localhost:7777'

async def fetch(session, url, json):
    return await session.post(url, json=json)

async def process_job(job_id):
    print(f"processing job: {job_id}")
    await asyncio.sleep(3)
    print("done.")

async def main():
    async with aiohttp.ClientSession() as session:
        while True:
            print("Ready for jobs.")
            request = { "auth": "worker1"}
            response = await fetch(session, JOB_SERVER + '/worker_job_request', request)
            response_text = await response.text()
#            print(f"{response.status} - {response_text}")
            if(response.status == 200):
                response_json = json.loads(response_text)

                job_id = response_json['job_id']
                wav_data = base64.b64decode(response_json['wav'])
                with open(f"job{job_id}.wav", 'wb') as audio_file:
                    audio_file.write(wav_data)

                await process_job(job_id)

                request = {}
                request['job_id'] = job_id
                request['text'] = 'You send the number ' + str(job_id)
                response = await fetch(session, JOB_SERVER + '/worker_job_result', request)
                response_text = await response.text()
                print(str(response_text))
            else:
                print("skipping job")

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
