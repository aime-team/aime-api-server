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

WEIGHT_FACTOR_ALPHA = 0.05

class JobState():
    UNKNOWN = 'unknown'
    QUEUED = 'queued'
    PROCESSING = 'processing'
    DONE = 'done'
    CANCELED = 'canceled'
    LAPSED = 'lapsed'


class WorkerState():
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
    def __init__(self, max_length, max_time):
        super().__init__(maxsize=max_length)
        self.max_length = max_length
        self.max_time = max_time


    @property
    def free_slots(self):
        return self.max_length - len(self)


    async def get(self, timeout=60):
        """Get job object of the next job in the queue.

        Returns:
            dict: Job object of the next job in the queue
        """        
        await self.remove_lapsed_jobs()
        return await asyncio.wait_for(super().get(), timeout=timeout)


    def fetch_waiting_job(self):
        """Get job data of the next waiting job in the queue. Returns None if no job is waiting

        Returns:
            dict: Job data of the next job in the queue, None if no job available
        """        
        try:
            job = self.get_nowait()
            self.task_done()
            return job
        except asyncio.QueueEmpty:
            return dict()


    def get_queue(self):
        return self._queue


    async def get_rank(self, job_id):
        await self.remove_lapsed_jobs()
        for rank, job in enumerate(self._queue):
            if job.id == job_id:
                return rank +1
        return 0


    def peek(self):
        if self._queue:
            return self._queue[0]
        return None

    def __len__(self):
        return len(self._queue)


    async def remove_lapsed_jobs(self):
        while self._queue:
            job = self.peek()
            if job and await job.state == JobState.LAPSED:
                self.get_nowait()
                self.task_done()
            else:
                break
                


class JobHandler():
    
    def __init__(self, app):
        """Job handler class to distribute api requests to the correct jobtypes and workers. 
        Provides methods for the worker, the endpoints and the AdminInterface() for job handling.

        Args:
            app (Sanic): Sanic server instance
        """        
        self.app = app
        self.job_types = self.init_all_job_types()
        self.lock = asyncio.Lock()


    def init_all_job_types(self):
        self.app.logger.info('--- creating job queues')
        job_types = dict()
        for endpoint in self.app.endpoints.values():
            job_type_name = endpoint.worker_job_type
            if job_type_name not in job_types:
                job_types[job_type_name] = JobType(self.app, endpoint)
        return job_types


    ### Worker methods

    async def worker_job_request(self, req_json):
        """Worker job request to the JobHandler. 
        Args:
            req_json (dict): Job request from worker

        Returns:
            dict: Job data of incoming job at a related endpoint or {'cmd': 'no_job'} if timed out.
        """        
        job_type = self.job_types.get(req_json.get('job_type'))
        if job_type:
            job_data = await job_type.worker_job_request(req_json)
        else:
            job_data = {'cmd': 'error', 'msg': f'No job queue found for job_type {job_type}'}
            self.app.logger.warning(
                f"Worker tried to send job request on unknown job_type {job_type}"
            )
        return job_data


    async def worker_update_progress_state(self, progress_result):
        """Update progress state with incoming progress updates from the worker to make it accessable to the endpoint. 
        Args:
            progress_result (dict): Progress result from worker

        Returns:
            dict: Response dict to worker with success message.
        """    
        job_type = self.job_types.get(progress_result.get('job_type'))
        job = self.get_job(progress_result.get('job_id'))
        if job_type:
            if job and job.result_future:
                response_cmd = await job_type.set_progress_state(progress_result)
            else:
                response_cmd = {'cmd': 'warning', 'msg': f'Job with job id {job.id} not valid'}
                self.app.logger.warning(
                    f"Worker tried to send progress for job {job.id} with "
                    f"job type {job_type}, but following error occured: {response_cmd.get('msg')}"
                )
        else:
            response_cmd = {'cmd': 'error', 'msg': f'No job queue found for job_type {job_type}'}
            self.app.logger.warning(
                f"Worker tried to send progress for job {job.id} with "
                f"job type {job_type}, but following error occured: {response_cmd.get('msg')}"
            )
        return response_cmd


    async def worker_set_job_result(self, req_json):
        """Set job result with incoming result from the worker to make it accessable to the endpoint. 
        Args:
            req_json (dict): Job result from worker

        Returns:
            dict: Response dict to worker with success message.
        """    
        self.app.logger.debug(f'Request on /worker_job_result: {shorten_strings(req_json)}')
        job = self.get_job(req_json.get('job_id'))
        job_type = self.job_types.get(req_json.get('job_type'))
        if job_type:
            if job and job.result_future:
                response_cmd = await job_type.set_job_result(req_json)
                self.app.logger.info(f"Worker '{req_json.get('auth')}' processed job {get_job_counter_id(job.id)}")
            else:
                response_cmd = {'cmd': 'warning', 'msg': f"Job {req_json.get('job_id')} invalid! Couldn't process job results!"}
                self.app.logger.warning(
                    f"Worker {req_json.get('auth')} tried to send job result for job {req_json.get('job_id')} with "
                    f"job type {job_type}, but following error occured: {response_cmd.get('msg')}"
                )
        else:
            response_cmd = {'cmd': 'error', 'msg': f'No job queue found for job_type {job_type}'}
            self.app.logger.warning(
                f"Worker {req_json.get('auth')} tried  to send job result for job {job.id} with "
                f"job type {job_type}, but following error occured: {response_cmd.get('msg')}"
            )
        return response_cmd


    ### Endpoint methods

    async def endpoint_new_job(self, job_data):
        """For endpoints: Init new job and put it to the related job queue.

        Args:
            job_data (dict): Job data of api request

        Returns:
            api_server.job_queue.Job: Newly created instance of Job()
        """
        endpoint_name = job_data.get('endpoint_name')
        job_type = self.get_job_type(endpoint_name=endpoint_name)
        if job_type:
            self.app.logger.debug(f'Client request on /{endpoint_name} with following input parameter: ')
            self.app.logger.debug(str(shorten_strings(job_data)))
            return await job_type.new_job(job_data)

    
    async def endpoint_get_progress_state(self, job):
        """For endpoints: Get current progress_state of job with given job id.

        Args:
            job (api_server.job_queue.Job): Instance of class Job

        Returns:
            dict: Current progress state of related job
        """
        job_type = self.get_job_type(job.id)
        if job_type:
            return await job_type.get_progress_state(job)


    async def endpoint_wait_for_job_result(self, job):
        """For endpoints: Wait for the final job result of job with given job id.

        Args:
            job (api_server.job_queue.Job): Instance of class Job

        Returns:
            dict: Current progress state of related job
        """
        job_type = self.get_job_type(job.id)
        if job_type:
            result = await job.result_future
            await self.finish_job(job)
            return result


    async def get_job_type_status(self, job_type_name):
        """Get current status information about the job type with given name.

        Args:
            job_type_name (str): Name of the job type

        Returns:
            dict: Current status information. Example: 
                {
                    'num_workers_online': 1,
                    'num_processing_requests': 1,
                    'num_pending_requests': 2,
                    'num_free_slots': 0
                }

        """        
        job_type = self.job_types.get(job_type_name)
        if job_type:
            return {
                'num_workers_online': await job_type.get_num_workers_online(),
                'num_processing_requests': job_type.get_num_running_jobs(),
                'num_pending_requests': len(job_type.queue),
                'num_free_slots': job_type.free_slots
            }


    ### Admin interface methods

    async def enable_worker(self, worker_auth):
        """Enable worker with given worker name 

        Args:
            worker_auth (str): Name of the worker

        Returns:
            bool: True if worker_auth is found in JobHandler() else False
        """        
        for job_type in self.job_types.values():
            if worker_auth in job_type.workers:
                worker = job_type.workers.get(worker_auth)
                await worker.enable()
                return True
        return False


    async def disable_worker(self, worker_auth):
        """Disable worker with given worker name 

        Args:
            worker_auth (str): Name of the worker

        Returns:
            bool: True if worker_auth is found in JobHandler() else False
        """        
        for job_type in self.job_types.values():
            if worker_auth in job_type.workers:
                worker = job_type.workers.get(worker_auth)
                await worker.disable()
                return True
        return False


    async def get_num_workers_online(self, job_type_name):
        """Get number of workers not in the state 'offline' connected to the job type with given name.

        Args:
            job_type_name (str): Name of the job type

        Returns:
            int: Number of workers being online
        """        
        job_type = self.job_types.get(job_type_name)
        if job_type:
            return await job_type.get_num_workers_online()


    async def get_all_workers(self, job_type_name=None):
        """Get a list of all worker objects. If job_type_name is given, return only the workers connected to the given job type.

        Args:
            job_type_name (str, optional): Name of the job type. Defaults to None.

        Returns:
            list[Worker, ]: List of all worker objects connected to given job type or all job types.
        """        
        if job_type_name:
            job_type = self.job_types.get(job_type_name)
            return await job_type.get_all_active_workers()
        else:
            return [worker for job_type in self.job_types.values() for worker in await job_type.get_all_workers()]


    async def get_all_active_workers(self, job_type_name=None):
        """Get a list of all worker objects not in the state 'offline'. If job_type_name is given, return only the workers connected to the given job type.

        Args:
            job_type_name (str, optional): Name of the job type. Defaults to None.

        Returns:
            list[Worker, ]: List of all online worker objects connected to given job type or all job types.
        """        
        if job_type_name:
            job_type = self.job_types.get(job_type_name)
            return await job_type.get_all_active_workers()
        else:
            return [worker for job_type in self.job_types.values() for worker in await job_type.get_all_active_workers()]


    async def get_worker_state(self, worker_auth):
        """Get the state of the worker with given name.

        Args:
            worker_auth (str): Name of the worker

        Returns:
            str: Current worker state: 'processing', 'waiting', 'offline' or 'disabled'
        """
        for job_type in self.job_types.values():
            if worker_auth in job_type.workers:
                return await job_type.get_worker_state(worker_auth)


    def get_worker_config(self, worker_auth):
        """Get the configuration of the worker with given name from the related endpoint configuration.

        Args:
            worker_auth (str): Name of the worker

        Returns:
            dict: Worker configuration containing job_type, worker_auth_key, etc.
        """        
        for job_type in self.job_types.values():
            if worker_auth in job_type.workers:
                for endpoint in self.app.endpoints.values():
                    if endpoint.worker_job_type == job_type.name:
                        return endpoint.config.get('WORKER', {})


    def get_worker_model(self, worker_auth):
        for job_type in self.job_types.values():
            worker = job_type.workers.get(worker_auth)
            if worker:
                return worker.model


    # Helper Methods

    async def finish_job(self, job):
        job_type = self.get_job_type(job.id)
        if job_type:
            await job_type.finish_job(job)


    async def is_job_queued(self, job_id):
        job_type = self.get_job_type(job_id)
        if job_type:
            return await job_type.is_job_queued(job_id)


    async def get_job_state(self, job_id):
        job_type = self.get_job_type(job_id)
        if job_type:
            return await job_type.get_job_state(job_id)
        else:
            return JobState.UNKNOWN


    def get_job(self, job_id):
        job_type = self.get_job_type(job_id)
        if job_type:
            return job_type.jobs.get(job_id)


    def get_result_future(self, job):
        job_type = self.get_job_type(job.id)
        if job_type:
            return job_type.get_result_future(job)


    def has_future(self, job_id):
        return bool(self.get_result_future(job_id))

    
    def get_free_queue_slots(self, endpoint_name):
        job_type = self.get_job_type(endpoint_name=endpoint_name)
        if job_type:
            return job_type.free_queue_slots


    def get_job_type(self, job_id=None, endpoint_name=None):
        if job_id:
            for job_type_name, job_type in self.job_types.items():
                if job_id in job_type.jobs:
                    return job_type
        elif endpoint_name:
            endpoint = self.app.endpoints.get(endpoint_name)
            if endpoint:
                return self.job_types.get(endpoint.worker_job_type)


    def validate_worker_request(self, req_json):
        job_type = self.job_types.get(req_json.get('job_type'))
        if job_type is None:
            if self.app.args.dev:
                return { 'cmd': "error", 'msg': f"No job queue for job_type: {job_type}" }
            else:
                return { 'cmd': "warning", 'msg': f"No job queue for job_type: {job_type}" }
        else:
            return job_type.validate_worker_request(req_json)


    def get_queue(self, endpoint_name):
        job_type = self.get_job_type(endpoint_name=endpoint_name)
        if job_type:
            return job_type.queue

    def get_worker(self, worker_auth):
        for job_type in self.job_types.values():
            if worker_auth in job_type.workers:
                return job_type.workers.get(worker_auth)
           

    async def job_request_timed_out(self, req_json):
        job_type = self.job_types.get(req_json.get('job_type'))
        if job_type:
            await job_type.job_request_timed_out(req_json)


    async def get_estimate_time(self, job_id):
        job_type = self.get_job_type(job_id)
        if job_type:
            return await job_type.get_estimate_time(job_id)
      

    def is_job_future_done(self, job):
        job_type = self.get_job_type(job.id)
        if job_type:
            return job_type.is_job_future_done(job)
        else:
            return False


    async def clean_up_jobs(self):
        for job_type in self.job_types.values():
            await job_type.clean_up_old_jobs()
            await job_type.clean_up_lapsed_jobs_in_all_workers()


    async def check_for_offline_workers(self):
        workers = await self.get_all_workers() # Check for offline workers already in get_all_workers


    async def set_worker_offline(self, auth):
        worker = self.get_worker(auth)
        await worker.set_state(WorkerState.OFFLINE)


          

class JobType():
    def __init__(self, app, endpoint):
        """Handles jobs, job queues, and the workers of all endpoints connected to this job type.

        Args:
            app (Sanic): Sanic server instance
            endpoint (Endpoint): Instance of class Endpoint
        """        
        self.app = app
        self.endpoint = endpoint
        self.name = endpoint.worker_job_type
        self.queue = JobQueue(endpoint.max_queue_length, endpoint.max_time_in_queue)
        self.app.logger.info(f'Queue for job type: {self.name} initialized')
        self.worker_auth_key = endpoint.worker_auth_key
        self.workers = dict() # key worker_auth
        self.jobs = dict() # key: job_id 


    @property
    def free_slots(self):
        return sum(worker.free_slots for worker in self.workers.values())

    @property
    def free_queue_slots(self):
        return self.queue.free_slots


    async def worker_job_request(self, req_json):

        worker_auth = req_json.get('auth')
        if worker_auth:
            if worker_auth in self.workers:
                worker = self.workers.get(worker_auth)
                if worker.model != WorkerModel(req_json):
                    self.app.logger.warning(f'Attention: Model attributes of worker {worker_auth} changed from {worker.model} to {WorkerModel(req_json)}')
                    worker.model = WorkerModel(req_json)
            else:
                worker = self.init_worker(req_json)
            await worker.register_job_request(req_json)
            job_id = None
            got_valid_job = False
            max_job_batch = req_json.get('max_job_batch', 1)
            while not got_valid_job:
                try:
                    job = await self.queue.get(timeout=req_json.get('request_timeout', 54) * 0.9)    # wait on queue for job
                    job_id = job.id
                    self.queue.task_done()   # take it out of the queue
                except asyncio.TimeoutError:
                    await self.job_request_timed_out(req_json)
                    return {'cmd': 'no_job'}
                got_valid_job = await self.is_job_queued(job_id)
            await self.start_job(job, req_json)

            job_batch_data = await self.fill_job_batch_with_waiting_jobs(job, req_json)
            return {
                'cmd': 'job',
                'api_server_version': __version__,
                'endpoint_name': self.endpoint.endpoint_name,
                'progress_output_descriptions': self.endpoint.ep_progress_param_config.get('OUTPUTS'),
                'final_output_descriptions': self.endpoint.ep_output_param_config,
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
                return await worker.finish_job(job)
            else:
                return {'cmd': 'error', 'msg': f'Job with job id {req_json.get("job_id")} not found in registered workers!'}


    async def new_job(self, job_data):
        job = await Job.new(job_data, self.app)
        self.jobs[job.id] = job 
        await self.queue.put(job)
        return job


    async def get_progress_state(self, job):
        if job:
            job.progress_state['queue_position'] = await job.queue_position
            job.progress_state['estimate'] = await self.get_estimate_time(job.id)
            job.progress_state['num_workers_online'] = await self.get_num_workers_online()
            if not job.progress_state.get('progress'):
                job.progress_state['progress'] = 0
            return job.progress_state


    async def start_job(self, job, req_json):
        worker = self.workers.get(req_json.get('auth'))
        if job and worker:
            await worker.start_job(job)
            if self.app.admin_backend:
                await self.app.admin_backend.admin_log_request_start_processing(
                    job.id,
                    job.start_time_compute,
                    await job.state
                )

    def get_num_running_jobs(self, endpoint_name=None):
        return sum(worker.get_num_running_jobs(endpoint_name) for worker in self.workers.values())


    async def is_job_queued(self, job_id):
        job = self.jobs.get(job_id)
        return await job.state == JobState.QUEUED if job else False


    def is_job_future_done(self, job):
        if job:
            return job.result_future.done() if job.result_future else False


    def get_result_future(self, job):
        if job:
            return job.result_future


    async def get_job_state(self, job_id):
        job = self.jobs.get(job_id)
        if job:
            return await job.state
        else:
            return JobState.UNKNOWN


    async def fill_job_batch_with_waiting_jobs(self, job, req_json):
        job = self.add_start_times(job) # backward compatibility for awi < 0.9.7. To be removed in future versions
        job_batch_data = [job.job_data]
        max_job_batch = req_json.get('max_job_batch')
        if max_job_batch > 1:
            while (len(job_batch_data) < max_job_batch):
                job = self.fetch_waiting_job()
                if job:
                    if await self.is_job_queued(job.id):
                        job = self.add_start_times(job) # backward compatibility for awi < 0.9.7. To be removed in future versions
                        job_batch_data.append(job.job_data)
                        await self.start_job(job, req_json)
                else:
                    break
        return job_batch_data


    def init_worker(self, req_json):
        worker = Worker(self.app, self, req_json)
        self.workers[req_json.get('auth')] = worker
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


    async def get_estimate_time(self, job_id):
        job = self.jobs.get(job_id)
        if job:
            job_state = await job.state
            if job_state == JobState.DONE:
                return 0
            elif job_state == JobState.PROCESSING:
                worker = self.workers.get(job.worker_auth)
                return worker.get_estimate_time(job)
            elif job_state == JobState.QUEUED:
                num_workers_online = await self.get_num_workers_online()
                if num_workers_online:
                    worker = next(iter(self.workers.values()))     
                    return max(
                        0,
                        calculate_estimate_time(
                            worker.mean_compute_duration * (await job.queue_position + 1) / num_workers_online,
                            job.start_time
                        )
                    )
                else:
                    return -1
            else:
                return -1


    async def get_num_workers_online(self):
        await self.check_for_offline_workers()
        return sum(worker.state is not WorkerState.OFFLINE for worker in self.workers.values())
       

    async def check_for_offline_workers(self):
        for worker in self.workers.values():
            await worker.check_for_offline_workers()


    async def get_all_workers(self):
        await self.check_for_offline_workers()
        return [worker for worker in self.workers.values()]


    async def get_all_active_workers(self):
        await self.check_for_offline_workers()
        return [worker for worker in self.workers.values() if not worker.state == WorkerState.OFFLINE]


    async def get_worker_state(self, worker_auth):
        worker = self.workers.get(worker_auth)
        if worker:
            return worker.state


    async def finish_job(self, job):
        if job:
            await job.finish()


    async def enable(self, worker_auth):
        worker = self.workers.get(worker_auth)
        if worker:
            await worker.enable()


    async def disable(self, worker_auth):
        worker = self.workers.get(worker_auth)
        if worker:
            await worker.disable()


    async def clean_up_old_jobs(self):
        for job in self.jobs.copy().values():
            if job.result_received_time and (time.time() - job.result_received_time) > job.result_lifetime:
                await self.app.admin_backend.admin_log_request_deleted(job.id)
                del self.jobs[job.id]


    async def clean_up_lapsed_jobs_in_all_workers(self):
        for worker in self.workers.values():
            await worker.clean_up_lapsed_jobs()


    def add_start_times(self, job):
        """Add start_time and start_time_compute for API Worker Interface < 0.9.7. To be removed in future versions.

        Args:
            job_data (dict): Job parameters
        """
        job.job_data['start_time'] = job.start_time
        job.job_data['start_time_compute'] = job.start_time_compute
        return job


class Worker():
    
    def __init__(self, app, job_type, req_json):
        """Worker object representing a GPU Worker instance.

        Args:
            app (Sanic): Sanic server instance
            job_type (str): Related job type
            req_json (dict): Request json of worker job request containing auth, job_request_timeout and model info
        """        
        self.app = app
        self.auth = req_json.get('auth')
        self.job_type = job_type
        self.lock = asyncio.Lock()
        self.state = WorkerState.WAITING
        self.num_finished_jobs = 0
        self.num_lapsed_jobs = 0
        self.retry = False
        self.max_batch_size = 0
        self.free_slots = 0
        self.last_request_time = time.time()
        self.job_request_timeout = req_json.get('request_timeout')
        self.model = WorkerModel(req_json)
        self.running_jobs = dict() # key job_id
        self.mean_compute_duration = int()


    async def set_state(self, new_state):
        if self.state != new_state:
            await self.app.admin_backend.admin_notify_worker_state_changed(self.auth, new_state)
            self.state = new_state


    async def enable(self):
        await self.set_state(WorkerState.WAITING)
        await self.check_for_offline_workers()


    async def disable(self):
        await self.set_state(WorkerState.DISABLED)


    def get_num_running_jobs(self, endpoint_name):
        return sum(1 for job in self.running_jobs.values() if not endpoint_name or job.endpoint_name == endpoint_name)


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
            await self.check_and_update_state()
            self.max_batch_size = req_json.get('max_job_batch', 1)
            self.free_slots = self.max_batch_size
            self.job_request_timeout = req_json.get('request_timeout', 60)


    async def job_request_timed_out(self):
        async with self.lock:
            self.retry = True


    async def start_job(self, job):
        if job:
            await job.start(self.auth)
            self.app.logger.info(f"Worker '{self.auth}' got job {get_job_counter_id(job.id)}")
            async with self.lock:
                self.free_slots += -1
                await self.check_and_update_state()
                await self.set_state(WorkerState.PROCESSING)
                self.running_jobs[job.id] = job


    async def set_progress_state(self, req_json):

        job_id = req_json.get('job_id')
        response_cmd = dict()
        async with self.lock:
            if job_id:
                job = self.running_jobs.get(job_id)
                if job:
                    await self.set_state(WorkerState.PROCESSING)
                    response_cmd = {'cmd': 'ok'}
            await self.check_and_update_state()
        return response_cmd


    async def finish_job(self, job):
        async with self.lock:
            self.num_finished_jobs += 1
            self.running_jobs.pop(job.id, None)
            self.mean_compute_duration = (1 - WEIGHT_FACTOR_ALPHA) * self.mean_compute_duration + WEIGHT_FACTOR_ALPHA * job.compute_duration
            await self.check_and_update_state()
        return {'cmd': 'ok'}


    async def check_and_update_state(self):
        self.last_request_time = time.time()
        if not self.running_jobs and not self.state == WorkerState.DISABLED:
            await self.set_state(WorkerState.WAITING)


    async def clean_up_lapsed_jobs(self):
        for job_id, job in self.running_jobs.copy().items():
            if await job.state == JobState.LAPSED:
                self.running_jobs.pop(job_id, None)
                self.num_lapsed_jobs += 1


    async def check_for_offline_workers(self):
        async with self.lock:
            if time.time() - self.last_request_time > 2 * self.job_request_timeout and not self.state == WorkerState.DISABLED:
                await self.set_state(WorkerState.OFFLINE)


    def get_estimate_time(self, job):
        return max(
            0,
            calculate_estimate_time(
                self.mean_compute_duration, 
                job.start_time_compute
            )
        )



class Job():
    id_counter = AtomicCounter()

    def __init__(self, job_data, app):
        """Job object representing API request containing progress state, result_future, 

        Args:
            job_data (dict): Job data of the client api request.
            app (Sanic): Sanic server instance.
        """
        self.id = job_data.get('job_id')
        self.endpoint_name = job_data.pop('endpoint_name')
        self.job_data = job_data
        self.app = app
        self.worker_auth = str()
        self.job_inactivity_timeout = self.app.endpoints.get(self.endpoint_name).clients_config.get('job_inactivity_timeout')
        self.max_time_in_queue = self.app.endpoints.get(self.endpoint_name).max_time_in_queue
        self.result_lifetime = self.app.endpoints.get(self.endpoint_name).clients_config.get('result_lifetime')
        self.last_update = time.time()
        self.__state = JobState.QUEUED
        self.progress_state = dict()
        self.lock = asyncio.Lock()
        self.result_future = asyncio.Future(loop=app.loop)
        self.start_time = time.time()
        self.start_time_compute = None
        self.result_received_time = None
        
        self.duration = None
        self.compute_duration = None
        self.pending_duration = None
        self.metrics = dict()


    @property
    async def state(self):
        if not self.__state == JobState.LAPSED and self.is_lapsed():
            self.__state = JobState.LAPSED
            self.result_received_time = time.time()
            if self.app.admin_backend:
                await self.app.admin_backend.admin_log_request_end(
                    self.id,
                    self.start_time_compute,
                    self.result_received_time,
                    self.__state,
                    request_error_msg=f'Job lapsed'
                )
        return self.__state


    def is_lapsed(self):
        now = time.time()
        if self.__state == JobState.QUEUED and (now - self.start_time) > self.max_time_in_queue:
            return True
        elif self.__state == JobState.PROCESSING and (now - self.last_update) > self.job_inactivity_timeout:
            worker = self.app.job_handler.get_worker(self.worker_auth)
            worker.running_jobs.pop(self.id)
            return True
        else:
            return False


    @classmethod
    async def new(cls, job_data, app):
        """Generates a new job ID using the asynchronous classmethod `generate_new_job_id` and 
        initializes a 'Job' object.

        Args:
            job_data (dict): Job data of the client api request.
            app (Sanic): Sanic server instance.

        Returns:
            Job: A new instance of Job.
        """    
        job_id = await cls.generate_new_job_id()
        job_data['job_id'] = job_id
        return cls(job_data, app)


    @classmethod
    async def generate_new_job_id(cls):
        counter = await cls.id_counter.next()
        return f'{uuid.uuid4()}#{counter}'

    @property
    async def queue_position(self):
        if await self.state == JobState.PROCESSING:
            return 0
        else:
            queue = self.app.job_handler.get_queue(self.endpoint_name)
            if queue is not None:
                return await queue.get_rank(self.id)
            else:
                return -1


    async def set_progress_state(self, req_json):
        async with self.lock:
            self.progress_state = req_json
            self.last_update = time.time()
            self.__state = JobState.PROCESSING


    async def set_job_result(self, req_json):
        async with self.lock:
            self.result_received_time = time.time()
            self.duration = self.result_received_time - self.start_time
            self.compute_duration = self.result_received_time - self.start_time_compute
            self.pending_duration = self.start_time - self.start_time_compute
            self.metrics = req_json.get('metrics', {})
            self.result_future.set_result(self.add_meta_data(req_json))



    async def start(self, worker_auth):
        async with self.lock:
            self.worker_auth = worker_auth
            self.__state = JobState.PROCESSING
            self.start_time_compute = time.time()


    async def finish(self):
        async with self.lock:
            self.__state = JobState.DONE
            self.progress_state.clear()


    def add_meta_data(self, req_json):
        if req_json:
            req_json['start_time'] = self.start_time
            req_json['start_time_compute'] = self.start_time_compute
            req_json['result_received_time'] = self.result_received_time
            req_json['total_duration'] = round(self.duration, 3)
            req_json['compute_duration'] = round(self.compute_duration, 3)
            if req_json.get('version'):
                req_json['worker_interface_version'] = req_json.pop('version')

        return req_json


class WorkerModel():
    def __init__(self, req_json):
        self.label = req_json.get('model_label', 'Unknown')
        self.quantization = req_json.get('model_quantization', 'Unknown')
        self.size = req_json.get('model_size', 'Unknown')
        self.family = req_json.get('model_family', 'Unknown')
        self.type = req_json.get('model_type', 'Unknown')
        self.repo_name = req_json.get('model_repo_name', 'Unknown')


    def __str__(self):
        return str(vars(self))


    def __eq__(self, other):
        if not isinstance(other, WorkerModel):
            return False
        return vars(self) == vars(other)


def calculate_estimate_time(estimate_duration, start_time):
    return round(estimate_duration - (time.time() - start_time), 1)


def weighted_average(nums, weights):
    return sum(x * y for x, y in zip(nums, weights)) / sum(weights)