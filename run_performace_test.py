# Copyright (c) AIME GmbH and affiliates. Find more info at https://www.aime.info/api
#
# This software may be used and distributed according to the terms of the AIME COMMUNITY LICENSE AGREEMENT

from api_test.api_test import ApiTest, load_flags

ENDPOINT = '/api_test'
WORKER_JOB_TYPE = 'api_test'
EP_CONFIG = 'api_test/endpoints/api_test_endpoint.cfg'
HOST = '0.0.0.0'
PORT = '7777'


def performance_test():
	"""Performance test of the API server requesting a high number of jobs on test workers with immediate responses.
	"""	
	args, _ = load_flags()
	args.hide_logging = True
	performance_test_single_worker = ApiTest(args, EP_CONFIG, 1)
	performance_test_single_worker.run_performance_tests()
	performance_test_single_worker.exit_processes()
	performance_test_two_workers = ApiTest(args, EP_CONFIG, 2)
	performance_test_two_workers.run_performance_tests()
	performance_test_two_workers.exit_processes()

if __name__ == "__main__":
	performance_test()
