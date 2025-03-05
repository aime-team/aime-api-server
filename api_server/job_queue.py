# Copyright (c) AIME GmbH and affiliates. Find more info at https://www.aime.info/api
#
# This software may be used and distributed according to the terms of the AIME COMMUNITY LICENSE AGREEMENT

import asyncio
import threading
from enum import Enum
import statistics
import time
from .utils.misc import shorten_strings, get_job_counter_id
import uuid
from .__version import __version__


class JobState(Enum):
    UNKNOWN = 'unknown'
    QUEUED = 'queued'
    PROCESSING = 'processing'
    DONE = 'done'
    CANCELED = 'canceled'


class WorkerState(Enum):
    PROCESSING = 'processing'
    WAITING = 'waiting'
    OFFLINE = 'offline'
    DISABLED = 'disabled'


class AtomicCounter():
    def __init__(self):
        self._counter = 0
        self._lock = asyncio.Lock()
        

    async def next(self):
        async with self._lock:
            self._counter += 1
            return self._counter


class JobQueue(asyncio.Queue):
    """Job queue to manage jobs for the given job type. Assignes jobs offered from client on APIEndpoint.api_request 
    via route /endpoint_name with a job_id and collects the job_data. The workers asking for jobs on worker_job_request_json get
    the job_data for the next job in the queue to process. Also monitors states of workers in registered_workers and mean_job_durations.

    """    
    def __init__(self):
        super().__init__()



    async def get(self, timeout=60):
        """Get job data of the next job in the queue. Timeout after self.job_request_timeout

        Returns:
            dict: Job data of the next job in the queue
        """        
                        
        return await asyncio.wait_for(super().get(), timeout=timeout)


    def fetch_waiting_job(self):
        """Get job data of the next waiting job in the queue. Returns None if no job is waiting

        Returns:
            dict: Job data of the next job in the queue, None if no job available
        """        
        try:
            job_data = self.get_nowait()
            self.task_done()
            return job_data
        except asyncio.QueueEmpty:
            return dict()


    def get_queue(self):
        return self._queue


    def get_rank(self, job_id):
        for rank, task in enumerate(self._queue):
            if task.get('job_id') == job_id:
                return rank +1
        return 0


    def __len__(self):
        return len(self._queue)


class JobHandler():

    def __init__(self, app):
        self.app = app
        self.job_types = self.init_all_job_types()
        self.lock = asyncio.Lock()


    async def worker_job_request(self, req_json):
        job_type = self.job_types.get(req_json.get('job_type'))
        if job_type:
            job_data = await job_type.worker_job_request(req_json)
        else:
            job_data = {'cmd': 'error', 'msg': f'No job queue found for job_type {job_type}'}
            self.app.logger.warning(
                f"Worker tried to send job request on unknown job_type {job_type}"
            )
        return job_data


    async def worker_update_progress_state(self, req_json):
        job_type = self.job_types.get(req_json.get('job_type'))
        job_id = req_json.get('job_id')
        if job_type:
            if self.has_future(job_id):
                response_cmd = await job_type.set_progress_state(req_json)
            else:
                response_cmd = {'cmd': 'warning', 'msg': f'Job with job id {job_id} not valid'}
                self.app.logger.warning(
                    f"Worker tried to send progress for job {job_id} with "
                    f"job type {job_type}, but following error occured: {response_cmd.get('msg')}"
                )
        else:
            response_cmd = {'cmd': 'error', 'msg': f'No job queue found for job_type {job_type}'}
            self.app.logger.warning(
                f"Worker tried to send progress for job {job_id} with "
                f"job type {job_type}, but following error occured: {response_cmd.get('msg')}"
            )
        return response_cmd


    async def worker_set_job_result(self, req_json):
        self.app.logger.debug(f'Request on /worker_job_result: {shorten_strings(req_json)}')
        job_id = req_json.get('job_id')
        job_type = self.job_types.get(req_json.get('job_type'))
        if job_type:
            if self.has_future(job_id):
                response_cmd = await job_type.set_job_result(req_json)
                self.app.logger.info(f"Worker '{req_json.get('auth')}' processed job {get_job_counter_id(job_id)}")
            else:
                job_id = f'unknown job {job_id}'
                response_cmd = {'cmd': 'warning', 'msg': f"Job {job_id} invalid! Couldn't process job results!"}
                self.app.logger.warning(
                    f"Worker {req_json.get('auth')} tried to send progress for job {job_id} with "
                    f"job type {job_type}, but following error occured: {response_cmd.get('msg')}"
                )
        else:
            response_cmd = {'cmd': 'error', 'msg': f'No job queue found for job_type {job_type}'}
            self.app.logger.warning(
                f"Worker {req_json.get('auth')} tried  to send progress for job {job_id} with "
                f"job type {job_type}, but following error occured: {response_cmd.get('msg')}"
            )
        return response_cmd

    
    async def endpoint_new_job(self, job_data):
        endpoint_name = job_data.get('endpoint_name')
        endpoint = self.app.endpoints.get(endpoint_name)
        if endpoint:
            self.app.logger.debug(f'Client request on /{endpoint_name} with following input parameter: ')
            self.app.logger.debug(str(shorten_strings(job_data)))
            job_type = self.job_types.get(endpoint.worker_job_type)
            return await job_type.new_job(job_data)

    
    async def endpoint_get_progress_state(self, job_id):
        job_type = self.get_job_type(job_id)
        if job_type:
            return await job_type.get_progress_state(job_id)


    async def endpoint_wait_for_job_result(self, job_id):
        job_type = self.get_job_type(job_id)
        if job_type:
            result_future = job_type.get_result_future(job_id)
            result = await result_future
            await self.finish_job(job_id)
            return result
    

    async def finish_job(self, job_id):
        job_type = self.get_job_type(job_id)
        if job_type:
            await job_type.finish_job(job_id)


    def is_job_queued(self, job_id):
        job_type = self.get_job_type(job_id)
        if job_type:
            return job_type.is_job_queued(job_id)


    def get_job_state(self, job_id):
        job_type = self.get_job_type(job_id)
        if job_type:
            return job_type.get_job_state(job_id)
        else:
            return JobState.UNKNOWN

    async def get_job_type_status(self, job_type_name):
        job_type = self.job_types.get(job_type_name)
        if job_type:
            return {
                'num_workers_online': await job_type.get_num_workers_online(),
                'num_processing_requests': job_type.get_num_running_jobs(),
                'num_pending_requests': len(job_type.queue),
                'mean_request_duration': job_type.mean_duration,
                'num_free_slots': job_type.free_slots
            }


    def get_result_future(self, job_id):
        job_type = self.get_job_type(job_id)
        if job_type:
            return job_type.get_result_future(job_id)


    def has_future(self, job_id):
        return bool(self.get_result_future(job_id))


    def init_all_job_types(self):
        self.app.logger.info('--- creating job queues')
        job_types = dict()
        for endpoint in self.app.endpoints.values():
            job_type_name = endpoint.worker_job_type
            if job_type_name not in job_types:
                job_types[job_type_name] = JobType(self.app, job_type_name, endpoint.worker_auth_key)
        return job_types


    def get_job_type(self, job_id):
        for job_type_name, job_type in self.job_types.items():
            if job_id in job_type.jobs:
                return job_type


    def validate_worker_request(self, req_json):
        job_type = self.job_types.get(req_json.get('job_type'))
        if job_type is None:
            if self.app.args.dev:
                return { 'cmd': "error", 'msg': f"No job queue for job_type: {job_type}" }
            else:
                return { 'cmd': "warning", 'msg': f"No job queue for job_type: {job_type}" }
        else:
            return job_type.validate_worker_request(req_json)


    def get_queue(self, job_type):
        return self.job_types.get(job_type).queue
           

    async def job_request_timed_out(self, req_json):
        job_type = self.job_types.get(req_json.get('job_type'))
        if job_type:
            await job_type.job_request_timed_out(req_json)


    async def start_job(self, job_id, req_json):
        job_type = self.job_types.get(req_json.get('job_type'))
        if job_type:
            await job_type.start_job(job_id, req_json)


    async def get_estimate_time(self, job_id):
        job_type = self.get_job_type(job_id)
        if job_type:
            return await job_type.get_estimate_time(job_id)


    async def get_num_workers_online(self, job_type_name):
        job_type = self.job_types.get(job_type_name)
        if job_type:
            return await job_type.get_num_workers_online()


    async def get_all_workers(self, job_type_name=None):
        if job_type_name:
            job_type = self.job_types.get(job_type_name)
            return await job_type.get_all_active_workers()
        else:
            return [worker for job_type in self.job_types.values() for worker in await job_type.get_all_workers()]


    async def get_all_active_workers(self, job_type_name=None):
        if job_type_name:
            job_type = self.job_types.get(job_type_name)
            return await job_type.get_all_active_workers()
        else:
            return [worker for job_type in self.job_types.values() for worker in await job_type.get_all_active_workers()]


    async def get_worker_state(self, worker_auth):
        for job_type in self.job_types.values():
            if worker_auth in job_type.workers:
                return await job_type.get_worker_state(worker_auth)


    def get_rank(self, job_id):    
        job_type = self.get_job_type(job_id)
        if job_type:
            return job_type.get_rank(job_id)
       

    def is_job_future_done(self, job_id):
        job_type = self.get_job_type(job_id)
        if job_type:
            return job_type.is_job_future_done(job_id)
        else:
            return False


    async def activate_worker(self, worker_auth):
        for job_type in self.job_types.values():
            if worker_auth in job_type.workers:
                worker = job_type.workers.get(worker_auth)
                await worker.activate()
                return True
        return False


    async def deactivate_worker(self, worker_auth):
        for job_type in self.job_types.values():
            if worker_auth in job_type.workers:
                worker = job_type.workers.get(worker_auth)
                await worker.deactivate()
                return True
        return False


class JobType():
    def __init__(self, app, name, worker_auth_key):
        self.app = app
        self.name = name
        self.queue = JobQueue()
        self.app.logger.info(f'Queue for job type: {name} initialized')
        self.worker_auth_key = worker_auth_key
        self.workers = dict() # key worker_auth
        #TODO delete finished jobs after certain time
        self.jobs = dict() # key: job_id 


    @property
    def free_slots(self):
        return sum(worker.free_slots for worker in self.workers.values())


    @property
    def mean_duration(self):
        if self.jobs:
            durations = [job.duration for job in self.jobs.values() if job.duration]
            if durations:
                return round(statistics.mean(durations), 2)
        return 200


    async def worker_job_request(self, req_json):

        worker_auth = req_json.get('auth')
        if worker_auth:
            worker = self.workers.get(worker_auth) or self.init_worker(worker_auth, req_json.get('request_timeout'))
            await worker.register_job_request(req_json)
            job_id = None
            got_valid_job = False
            max_job_batch = req_json.get('max_job_batch', 1)
            while not got_valid_job:
                try:
                    job_data = await self.queue.get(timeout=req_json.get('request_timeout', 54) * 0.9)    # wait on queue for job
                    self.queue.task_done()   # take it out of the queue
                except asyncio.TimeoutError:
                    await self.job_request_timed_out(req_json)
                    return {'cmd': 'no_job'}

                job_id = job_data.get('job_id')
                if self.app.is_client_valid(job_data):
                    got_valid_job = self.is_job_queued(job_id)
            await self.start_job(job_id, req_json)

            job_batch_data = await self.fill_job_batch_with_waiting_jobs(job_data, req_json)

            endpoint_name = job_data.pop('endpoint_name', '')          
            endpoint = self.app.endpoints.get(endpoint_name)
            return {
                'cmd': 'job',
                'api_server_version': __version__,
                'endpoint_name': endpoint_name,
                'progress_output_descriptions': endpoint.ep_progress_param_config.get('OUTPUTS'),
                'final_output_descriptions': endpoint.ep_output_param_config,
                'job_data': job_batch_data
            }


    async def set_progress_state(self, req_json):
        job = self.jobs.get(req_json.get('job_id'))
        if job:
            await job.set_progress_state(req_json)
            worker = self.workers.get(job.worker_auth)
            if worker:
                return await worker.set_progress_state(req_json)
            else:
                return {'cmd': 'error', 'msg': f'Job with job id {req_json.get("job_id")} not found in registered workers!'}
        else:
            return {'cmd': 'error', 'msg': f'Job with job id {req_json.get("job_id")} not found in registered workers!'}


    async def set_job_result(self, req_json):

        job = self.jobs.get(req_json.get('job_id'))
        worker = self.workers.get(req_json.get('auth'))
        if job and worker:
            if worker:
                await job.set_job_result(req_json)
                return await worker.set_job_result(req_json)
            else:
                return {'cmd': 'error', 'msg': f'Job with job id {req_json.get("job_id")} not found in registered workers!'}


    async def new_job(self, job_data):
        job = await Job.new(job_data.get('endpoint_name'), self.queue, self.app.loop)
        self.jobs[job.id] = job 
        job_data['job_id'] = job.id
        self.app.logger.info(f"Client {job_data.get('client_session_auth_key')} putting job {get_job_counter_id(job.id)} into the '{self.name}' queue ... ")
        await self.queue.put(job_data)
        return job


    async def get_progress_state(self, job_id):
        job = self.jobs.get(job_id)
        if job:
            job.progress_state['queue_position'] = job.queue_position
            job.progress_state['estimate'] = await self.get_estimate_time(job_id)
            job.progress_state['num_workers_online'] = await self.get_num_workers_online()
            if not job.progress_state.get('progress'):
                job.progress_state['progress'] = 0
            return job.progress_state


    async def start_job(self, job_id, req_json):
        job = self.jobs.get(job_id)
        worker = self.workers.get(req_json.get('auth'))
        if job and worker:        
            await worker.start_job(job)


    def get_num_running_jobs(self, endpoint_name=None):
        return sum(worker.get_num_running_jobs(endpoint_name) for worker in self.workers.values())


    def is_job_queued(self, job_id):
        job = self.jobs.get(job_id)
        return job.state == JobState.QUEUED if job else False


    def is_job_future_done(self, job_id):
        job = self.jobs.get(job_id)
        if job:
            return job.result_future.done() if job.result_future else False


    def get_result_future(self, job_id):
        job = self.jobs.get(job_id)
        if job:
            return job.result_future


    def get_job_state(self, job_id):
        job = self.jobs.get(job_id)
        if job:
            return job.state
        else:
            return JobState.UNKNOWN


    async def fill_job_batch_with_waiting_jobs(self, job_data, req_json):
        job_data = self.add_start_times(job_data) # backward compatibility for awi < 0.9.7. To be removed in future versions
        job_batch_data = [job_data]
        max_job_batch = req_json.get('max_job_batch')
        if max_job_batch > 1:
            while (len(job_batch_data) < max_job_batch):
                job_data = self.fetch_waiting_job()
                if job_data:
                    if self.app.is_client_valid(job_data):
                        job_id = job_data.get('job_id')
                        if self.is_job_queued(job_id):
                            job_data = self.add_start_times(job_data) # backward compatibility for awi < 0.9.7. To be removed in future versions
                            job_batch_data.append(job_data)
                            await self.start_job(job_id, req_json)
                else:
                    break
        return job_batch_data


    def init_worker(self, auth, request_timeout=60):
        worker = Worker(self.app, auth, self, request_timeout)
        self.workers[auth] = worker
        return worker


    async def job_request_timed_out(self, req_json):
        worker = self.workers.get(req_json.get('auth'))
        if worker:
            await worker.job_request_timed_out()


    def validate_worker_request(self, req_json):
        if self.worker_auth_key != req_json.get('auth_key'):
            return { 'cmd': "error", 'msg': f"Worker not authorized!" }
        else: 
            return {'cmd': 'ok'}


    def fetch_waiting_job(self):
        if self.queue:
            return self.queue.fetch_waiting_job()
        else:
            return dict()


    def get_rank(self, job_id):
        return self.queue.get_rank(job_id)
 

    async def get_estimate_time(self, job_id):
        job = self.jobs.get(job_id)
        if job:
            worker = self.workers.get(job.worker_auth)
            if not worker:
                if self.workers:
                    worker = next(iter(self.workers.values()))
                else:
                    return -1
            return await worker.get_estimate_time(job)


    async def get_num_workers_online(self):
        await self.update_offline_workers_state()
        return sum(worker.state is not WorkerState.OFFLINE for worker in self.workers.values())
       

    async def update_offline_workers_state(self):
        for worker in self.workers.values():
            await worker.update_offline_state()


    async def get_all_workers(self):
        await self.update_offline_workers_state()
        return [worker.auth for worker in self.workers.values()]


    async def get_all_active_workers(self):
        await self.update_offline_workers_state()
        return [worker.auth for worker in self.workers.values() if not worker.state == WorkerState.OFFLINE]


    async def get_worker_state(self, worker_auth):
        worker = self.workers.get(worker_auth)
        if worker:
            return worker.state


    async def finish_job(self, job_id):
        job = self.jobs.get(job_id)
        if job:
            await job.finish()


    async def activate(self, worker_auth):
        worker = self.workers.get(worker_auth)
        if worker:
            await worker.activate()


    async def deactivate(self, worker_auth):
        worker = self.workers.get(worker_auth)
        if worker:
            await worker.deactivate()


    def add_start_times(self, job_data):
        """Add start_time and start_time_compute for API Worker Interface < 0.9.7. To be removed in future versions.

        Args:
            job_data (dict): Job parameters
        """
        job = self.jobs.get(job_data.get('job_id'))
        job_data['start_time'] = job.start_time
        job_data['start_time_compute'] = job.start_time_compute
        return job_data


class Worker():
    
    def __init__(self, app, auth, job_type, job_request_timeout=60):
        self.app = app
        self.auth = auth
        self.job_type = job_type
        self.lock = asyncio.Lock()
        self.state = WorkerState.WAITING
        self.num_finished_jobs = 0
        self.num_timed_out_jobs = 0
        self.retry = False
        self.free_slots = 0
        self.last_request_time = time.time()
        self.job_request_timeout = job_request_timeout
        self.running_jobs = dict() # key job_id


    async def activate(self):
        self.state = WorkerState.WAITING
        await self.update_offline_state()


    async def deactivate(self):
        self.state = WorkerState.DISABLED


    def get_num_running_jobs(self, endpoint_name):
        return sum(1 for job in self.running_jobs.values() if not endpoint_name or job.endpoint_name == endpoint_name)


    @property
    def mean_compute_duration(self):
        if self.job_type.jobs:
            durations = [job.compute_duration for job in self.job_type.jobs.values() if self.auth == job.worker_auth and job.compute_duration]
            if durations:
                return round(statistics.mean(durations), 2)
        return 7.5


    async def register_job_request(self, req_json):
        logger_string = (
            f"Worker '{req_json.get('auth')}' in version {req_json.get('worker_version')} "
            f"with {req_json.get('version')} waiting on '{req_json.get('job_type')}' queue for a job ..."
        )
        async with self.lock:
            if not self.retry:
                self.app.logger.info(logger_string)
            else:
                self.app.logger.debug(logger_string)
                self.retry = False
            self.check_and_update_state()
            self.free_slots = req_json.get('max_job_batch', 1)
            self.job_request_timeout = req_json.get('request_timeout', 60)


    async def job_request_timed_out(self):
        async with self.lock:
            self.retry = True


    async def start_job(self, job):
        await job.start(self.auth, 2 * self.job_request_timeout)
        self.app.logger.info(f"Worker '{self.auth}' got job {get_job_counter_id(job.id)}")
        async with self.lock:
            self.free_slots += -1
            self.check_and_update_state()
            self.state = WorkerState.PROCESSING
            self.running_jobs[job.id] = job


    async def set_progress_state(self, req_json):

        job_id = req_json.get('job_id')
        response_cmd = dict()
        async with self.lock:
            if job_id:
                job = self.running_jobs.get(job_id)
                if job:
                    self.state = WorkerState.PROCESSING
                    response_cmd = {'cmd': 'ok'}
            self.check_and_update_state()
        return response_cmd


    async def set_job_result(self, req_json):
        async with self.lock:
            self.num_finished_jobs += 1
            self.running_jobs.pop(req_json.get('job_id'), None)
            self.check_and_update_state()
        return {'cmd': 'ok'}


    def check_and_update_state(self):
        self.last_request_time = time.time()
        for job_id, job in self.running_jobs.copy().items():
            if not job.is_alive():
                self.running_jobs.pop(job_id)
                self.num_timed_out_jobs += 1
        if not self.running_jobs and not self.state == WorkerState.DISABLED:
            self.state = WorkerState.WAITING


    async def update_offline_state(self):
        async with self.lock:
            if time.time() - self.last_request_time > 2 * self.job_request_timeout and not self.state == WorkerState.DISABLED:
                self.state = WorkerState.OFFLINE


    async def get_estimate_time(self, job):
        if job.state == JobState.QUEUED:
            num_workers_online = await self.job_type.get_num_workers_online()
            if num_workers_online and job.queue_position:                
                return max(
                    calculate_estimate_time(
                        self.mean_compute_duration * (job.queue_position + 1) / num_workers_online,
                        job.start_time
                    ),
                    calculate_estimate_time(
                        self.job_type.mean_duration,
                        job.start_time
                    )
                )
            else:
                return -1

        elif job.state == JobState.PROCESSING:
            return max(
                0,
                calculate_estimate_time(
                    self.mean_compute_duration, 
                    job.start_time_compute
                )
            )

        elif job.state == JobState.DONE:
            return 0
        else:
            return -1


class Job():

    id_counter = AtomicCounter()

    def __init__(self, job_id, endpoint_name, queue, loop):

        self.id = job_id
        self.endpoint_name = endpoint_name
        self.queue = queue
        self.worker_auth = str()
        self.timeout = int()
        self.last_update = time.time()
        self.state = JobState.QUEUED
        self.progress_state = dict()
        self.lock = asyncio.Lock()
        self.result_future = asyncio.Future(loop=loop)
        self.start_time = time.time()
        self.start_time_compute = None
        self.result_received_time = None
        self.duration = None
        self.compute_duration = None
        self.pending_duration = None


    @classmethod
    async def new(cls, endpoint_name, queue, loop):
        job_id = await cls.generate_new_job_id()
        return cls(job_id, endpoint_name, queue, loop)


    @classmethod
    async def generate_new_job_id(cls):
        counter = await cls.id_counter.next()
        return f'{uuid.uuid4()}#{counter}'

    @property
    def queue_position(self):
        return self.queue.get_rank(self.id)



    async def set_progress_state(self, req_json):
        async with self.lock:
            self.timeout = 2 * req_json.get('request_timeout', 60)
            self.progress_state = req_json
            self.last_update = time.time()
            self.state = JobState.PROCESSING


    async def set_job_result(self, req_json):
        async with self.lock:
            self.result_received_time = time.time()
            self.duration = self.result_received_time - self.start_time
            self.compute_duration = self.result_received_time - self.start_time_compute
            self.pending_duration = self.start_time - self.start_time_compute
            self.result_future.set_result(self.add_meta_data(req_json))
            


    async def start(self, worker_auth, timeout):
        
        async with self.lock:
            self.worker_auth = worker_auth
            self.timeout = timeout
            self.state = JobState.PROCESSING
            self.start_time_compute = time.time()


    async def finish(self):
        async with self.lock:
            self.state = JobState.DONE
            self.progress_state.clear()


    def is_alive(self):
        return False if time.time() - self.last_update > self.timeout else True


    def add_meta_data(self, req_json):
        if req_json:
            req_json['start_time'] = self.start_time
            req_json['start_time_compute'] = self.start_time_compute
            req_json['result_received_time'] = self.result_received_time
            req_json['total_duration'] = self.duration
            req_json['compute_duration'] = self.compute_duration
            if req_json.get('version'):
                req_json['worker_interface_version'] = req_json.pop('version')
        return req_json


def calculate_estimate_time(estimate_duration, start_time):
    return round(estimate_duration - (time.time() - start_time), 1)


def weighted_average(nums, weights):
    return sum(x * y for x, y in zip(nums, weights)) / sum(weights)