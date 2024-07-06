# Copyright (c) AIME GmbH and affiliates. Find more info at https://www.aime.info/api
#
# This software may be used and distributed according to the terms of the AIME COMMUNITY LICENSE AGREEMENT

import asyncio
import threading
from enum import Enum
import statistics
import time


class JobState(Enum):
    UNKNOWN = "unknown"
    QUEUED = "queued"
    PROCESSING = "processing"
    DONE = "done"
    CANCELED = "canceled"


class AtomicCounter():
    def __init__(self):
        self._counter = 0
        self._lock = threading.Lock()
        
    def next(self):
        job_id = 0
        with self._lock:
            self._counter += 1
            job_id = self._counter
        return "JID" + str(job_id)


class JobQueue():
    """Job queue to manage jobs for the given job type. Assignes jobs offered from client on APIEndpoint.api_request 
    via route /endpoint_name with a job_id and collects the job_data. The workers asking for jobs on worker_job_request_json get
    the job_data for the next job in the queue to process. Also monitors states of workers in registered_workers and mean_job_durations.

    Args:
        job_type (str): Job type
        worker_auth_key (str): Key for worker authorization
    """    
    job_id = AtomicCounter()    # this has to be an atomic counter

    def __init__(self, job_type, worker_auth_key):
        """_summary_

        Args:
            job_type (_type_): _description_
            worker_auth_key (_type_): _description_
        """        
        self.job_type = job_type
        self.worker_auth_key = worker_auth_key
        self.queue = asyncio.Queue()
        self.job_durations = {
            'total_duration': [], 
            'compute_duration':[]
        }
        self.mean_job_duration = {
            'total_duration': 200,        
            'compute_duration': 7.5
        }
        self.registered_workers = dict()


    def get_next_job_id(self):
        
        return JobQueue.job_id.next()


    async def get(self, job_timeout=60):
        """Get job data of the next job in the queue. Timeout after self.job_timeout

        Returns:
            dict: Job data of the next job in the queue
        """        
        return await asyncio.wait_for(self.queue.get(), timeout=job_timeout)

    def fetch_waiting_job(self):
        """Get job data of the next waiting job in the queue. Returns None if no job is waiting

        Returns:
            dict: Job data of the next job in the queue, None if no job available
        """        
        try:
            job_data = self.queue.get_nowait()
            self.queue.task_done()
        except asyncio.QueueEmpty:
            job_data = None
        return job_data


    def task_done(self):
        return self.queue.task_done()


    async def put(self, job_data):
        """Put job_data from the client job offer to the job_queue.

        Args:
            job_data (dict): Job data of the job

        Returns:
            _type_: _description_
        """        
        return await self.queue.put(job_data)


    def get_queue(self):
        return self.queue._queue


    def get_rank_for_job_id(self, job_id):
        queue = self.get_queue()
        for rank, task in enumerate(queue):
            if task.get('job_id') == job_id:
                return rank +1

 

    def get_start_time_for_job_id(self, job_id):
        queue = self.get_queue()
        for task in queue:
            if task.get('job_id') == job_id:
                return task.get('start_time')


    def get_num_jobs_for_client(self, client_session_auth_key):
        num_jobs = 0
        queue = self.get_queue()
        if client_session_auth_key:
            for task in enumerate(queue):
                if task.get('client_session_auth_key') == client_session_auth_key:
                    num_jobs += 1
        return num_jobs


    def update_mean_job_duration_weighted_mean(
        self,
        result,
        update_interval=1,
        weight=10
        ):
        

        for key, parameter in result.items():
            if key in self.job_durations:
                job_durations = self.job_durations[key]
                job_durations.append(result[key])

                if len(job_durations) >= update_interval:
                    job_durations.insert(0, self.mean_job_duration[key])
                    weigths = [1 if idx != 0 else weight for idx in range(update_interval + 1) ]
                    self.mean_job_duration[key] =  weighted_average(job_durations, weights)
                    job_durations.clear()

                self.job_durations[key] = job_durations


    def update_mean_job_duration(
        self,
        result,
        update_interval=1,
        length=100,
        ):

        for key, parameter in result.items():
            if key in self.job_durations:
                job_durations = self.job_durations[key]
                job_durations.append(result[key])

                if len(job_durations) % update_interval == 0:
                    self.mean_job_duration[key] = round(statistics.mean(job_durations), 2)
                    if len(job_durations) > length:
                        job_durations = job_durations[update_interval:]
                self.job_durations[key] = job_durations

    def update_worker_status(self):
        for worker in self.registered_workers.values():
            last_request_time_limit = max(2 * worker.get('job_timeout', 54) + self.mean_job_duration.get('compute_duration'), 60)
            if (time.time() - worker.get('last_request')) > last_request_time_limit:
                worker['status'] = 'offline'



def weighted_average(nums, weights):
    return sum(x * y for x, y in zip(nums, weights)) / sum(weights)