# minimal example worker to request a job batch and sends results

from aime_api_worker_interface import APIWorkerInterface
import time

WORKER_JOB_SERVER = 'http://localhost:7777'
WORKER_JOB_TYPE = "example_worker"
WORKER_AUTH_KEY = "869a93805a301f8a41e0610129a72b19"

MAX_JOB_BATCH = 2


FRAME_RATE = 150

def main():

    api_worker = APIWorkerInterface(WORKER_JOB_SERVER, WORKER_JOB_TYPE, WORKER_AUTH_KEY)

    while True:
        print('--- waiting for jobs of type: ' + WORKER_JOB_TYPE)
        job_batch_data = api_worker.job_batch_request(max_job_batch=MAX_JOB_BATCH)
        for job_data in job_batch_data:
            print('- received job: ', job_data)

        job_step_counter = [0] * MAX_JOB_BATCH
        job_step_duration = [0] * MAX_JOB_BATCH
        job_sleep_counter = [0] * MAX_JOB_BATCH
        job_finished = [False] * MAX_JOB_BATCH

        for idx, job_data in enumerate(job_batch_data):
            sleep_duration = float(job_data['sleep_duration'])
            progress_steps = int(job_data['progress_steps'])
            job_step_duration[idx] = sleep_duration
            if(progress_steps > 0):
                job_step_duration[idx] = (FRAME_RATE * sleep_duration) / progress_steps

        all_jobs_finished = False

        while not all_jobs_finished:
            for idx, job_data in enumerate(job_batch_data):
                if job_finished[idx]:
                    continue

                if job_sleep_counter[idx] >= job_step_duration[idx]:
                    progress_steps = int(job_data['progress_steps'])
                    if job_step_counter[idx] >= progress_steps:
                        # job finished
                        job_finished[idx] = True
                        print(job_data['job_id'] + ": finished.")

                        results = {}
                        counter = job_data['counter'] + 1
                        results['text'] = f"request #{counter} done. You sent: {job_data['prompt']}"
                        results['counter'] = counter
                        api_worker.send_job_results(results, job_data=job_data)
                    else:
                        # step update
                        step_str = 'step ' + str(job_step_counter[idx])
                        print(job_data['job_id'] + ": " + step_str  + "/" +  str(progress_steps))
                        progress_data = {}
                        progress_data['status'] = step_str
                        api_worker.send_progress((100.0 * (job_step_counter[idx] + 1)) / progress_steps, progress_data, job_data=job_data)
                        job_step_counter[idx] += 1
                        job_sleep_counter[idx] = 0
                else:
                    job_sleep_counter[idx] += 1

            time.sleep(1.0 / FRAME_RATE)   # simulate work

            # check if all jobs have finished
            all_jobs_finished = True
            for idx in range(len(job_batch_data)):
                if not job_finished[idx]:
                    all_jobs_finished = False
                    break



if __name__ == "__main__":
    main()