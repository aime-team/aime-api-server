from api_client_interface.python.model_api import do_api_request
import toml
import asyncio
import argparse
import time
from tqdm import tqdm
from collections import Counter

class BenchmarkApi():

    def __init__(self):
        self.args = self.load_flags()
        self.progress_bar_dict = dict()
        self.title_bar = tqdm(total=0, bar_format='{desc}', leave=False)
        self.num_generated_tokens = 480

    
    def load_flags(self):
        parser = argparse.ArgumentParser()
        parser.add_argument(
            '-as', '--api_server', type=str, default="http://0.0.0.0:7777", required=False, help='Address of api-server'
                            )
        parser.add_argument(
            '-tr', '--total_requests', type=int, default=2, required=False
                            )
        parser.add_argument(
            '-cf', '--config_file', type=str, required=False
                            )
        parser.add_argument(
            '-ep', '--endpoint_name', type=str, default='stable_diffusion_xl_txt2img', required=False
                            )
        args = parser.parse_args()
        if not args.config_file:
            if args.endpoint_name == 'stable_diffusion_xl_txt2img':
                args.config_file = 'endpoints/stable_diffusion_xl/txt2img/ml_api_endpoint.cfg'
            else:
                args.config_file = f'endpoints/{args.endpoint_name}/ml_api_endpoint.cfg'
        return args

    def get_default_values_from_config(self):
        with open(self.args.config_file, "r") as f:
            config = toml.load(f)
        ep_inputs = config.get('INPUTS', {})
        params = dict()
        for ep_input in ep_inputs:
            params[ep_input] = ep_inputs[ep_input].get('default')
        if params.get('seed'):
            params['seed'] = 1
        if params.get('top_k'):
            params['top_k'] = 1
            params['top_p'] = 1
            params['text'] = 'Once upon a time'
        return params

    def run(self):
        params = self.get_default_values_from_config()
        loop = self.get_loop()
        start = time.time()
        tasks = [asyncio.ensure_future(do_api_request(self.args.api_server, self.args.endpoint_name, params, self.result_callback, self.progress_callback)) for _ in range(self.args.total_requests)]
        loop.run_until_complete(asyncio.gather(*tasks))
        duration = round(time.time() - start)
        self.title_bar.close()
        summary_string = f'\n{self.args.total_requests} requests on {self.args.api_server} took {duration} seconds.\nMean time per request: {duration/self.args.total_requests}s'
        if self.args.endpoint_name == 'llama2_chat':
            summary_string += f'; {round((self.args.total_requests*self.num_generated_tokens)/duration, 1)} tokens/s'
        else:
            summary_string += f'; {round(self.args.total_requests/duration, 1)} images/s'
            
        print(summary_string)
    def get_loop(self):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop

    def progress_callback(self, progress_info, progress_data):
        job_id = progress_info['job_id']
        #print(progress_info, progress_data)
        if not self.progress_bar_dict.get(job_id):
            if progress_info['queue_position'] == 0:
                self.progress_bar_dict[job_id] = tqdm(range(0, 100), desc=f'Current job: {job_id}', leave=False)
            else:
                self.progress_bar_dict[job_id] = None

        waiting_tasks = Counter(self.progress_bar_dict.values())[None]
        self.title_bar.set_description_str(f'Remaining jobs: {waiting_tasks}')
        current_progress_bar = self.progress_bar_dict[job_id]
        if current_progress_bar:
            if self.args.endpoint_name == 'llama2_chat':
                current_progress_bar.n = round(100*progress_info['progress']/self.num_generated_tokens)
            else:
                current_progress_bar.n = progress_info['progress']
            current_progress_bar.refresh()
            current_progress_bar.set_description(f'Current job: {job_id}')
            #self.remove_progress_bar_when_finished(job_id)
        

    def result_callback(self, result):
        self.num_generated_tokens = result.get('num_generated_tokens')
        self.remove_progress_bar_when_finished(result['job_id'])
        
        #result.pop('images')
        #print('result ', result)
        
    def remove_progress_bar_when_finished(self, job_id):
        current_progress_bar = self.progress_bar_dict.get(job_id)
        if current_progress_bar:# or progress_info['progress'] == 100:
            current_progress_bar.close()
            del self.progress_bar_dict[job_id]



def main():
    benchmark_api = BenchmarkApi()
    benchmark_api.run()


if __name__ == "__main__":
	main()
