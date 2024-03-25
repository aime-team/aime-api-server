# Copyright (c) AIME GmbH and affiliates. Find more info at https://www.aime.info/api
#
# This software may be used and distributed according to the terms of the AIME COMMUNITY LICENSE AGREEMENT

from aime_api_worker_interface import APIWorkerInterface
import argparse
import time
from PIL import Image, UnidentifiedImageError
import numpy as np
import base64
import io

WORKER_JOB_TYPE = "api_test"
WORKER_AUTH_KEY = "5b07e305b50505ca2b3284b4ae5f65d2"



class ApiTestWorker():
    def __init__(self, args):
        self.args = args
        self.api_worker_interface = APIWorkerInterface(self.args.api_server, self.args.worker_job_type, self.args.worker_auth_key, print_server_status=False)
        while True:
            self.job_data = self.check_job_request()
            self.error_handling()
            #time.sleep(0.1)
            self.send_test_job_result_with_progress()
                

    def check_job_request(self):
        job_data = self.api_worker_interface.job_request()
        return job_data


    def send_test_job_result_with_progress(self):
        
        test_results = {'text': 'Test output'}
        if self.job_data.get('image'):
            # Sending the client output image rescaled in api_endpoint back to client as result, to test rescaling
            image_list = [convert_base64_string_to_image(self.job_data['image'])]

            test_results['images'] = image_list
        steps = 10
        for step in range(steps):
            #time.sleep(0.2) # Simulate calculation
            progress = (step+1)*100/steps
            if self.api_worker_interface.progress_data_received:
                self.api_worker_interface.send_progress(progress, test_results)
        
        self.api_worker_interface.send_job_results(test_results)
        
    def error_handling(self):
        if self.job_data.get('cmd') == 'error':
            raise ConnectionRefusedError(job_data['msg'])

def load_flags():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--api_server", type=str, default='http://0.0.0.0:7777', required=False,
        help="Address of job server"
    )
    parser.add_argument(
        "--worker_job_type", type=str, default="api_test", required=False,
        help="worker_job_type"
    )
    parser.add_argument(
        "--worker_auth_key", type=str, default="5b07e305b50505ca2b3284b4ae5f65d2", required=False,
        help="worker_auth_key"
    )

    return parser.parse_args()

def convert_base64_string_to_image(base64_string):
    base64_data = base64_string.split(',')[1]
    image_data = base64.b64decode(base64_data)
    with io.BytesIO(image_data) as buffer:
        image = Image.open(buffer)
        return image.copy()



def main():
    args = load_flags()
    api_test_worker = ApiTestWorker(args)
    

if __name__ == "__main__":
    main()