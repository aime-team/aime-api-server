# minimal example worker to request a job and send results

import sys
sys.path.append('../..')
from aime_api_worker_interface import APIWorkerInterface
import time

WORKER_JOB_SERVER = 'http://localhost:7777'
WORKER_JOB_TYPE = "example_worker"
WORKER_AUTH_KEY = "869a93805a301f8a41e0610129a72b19"

def main():

    api_worker = APIWorkerInterface(WORKER_JOB_SERVER, WORKER_JOB_TYPE, WORKER_AUTH_KEY)

    while True:
        print('--- waiting for jobs of type: ' + WORKER_JOB_TYPE)
        job_batch_data = api_worker.job_batch_request(max_job_batch=2)
        for job_data in job_batch_data:
            print('- received job: ', job_data)

        job_data = job_batch_data[0]

        sleep_duration = float(job_data['sleep_duration'])
        progress_steps = int(job_data['progress_steps'])
        progress_data = {}
        print(f"- working for {sleep_duration} seconds with {progress_steps} steps")
        if(progress_steps > 0):
            step_duration = sleep_duration / progress_steps
            for step in range(progress_steps):
                time.sleep(step_duration)
                step_str = 'step ' + str(step) 
                print(step_str)
                progress_data['status'] = step_str
                api_worker.send_progress((100.0 * (step + 1)) / progress_steps, progress_data, job_data=job_data)
        else:
            time.sleep(sleep_duration)   # simulate work

        for job_data in job_batch_data:
            results = {}
            counter = job_data['counter'] + 1
            results['text'] = f"request #{counter} done. You sent: {job_data['prompt']}"
            results['counter'] = counter
            api_worker.send_job_results(results, job_data=job_data)


if __name__ == "__main__":
    main()