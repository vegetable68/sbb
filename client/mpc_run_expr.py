import json
import os
import psutil
import numpy as np
import time

CONFIG_PATH = '../config.json'
RESULTS_PATH = '../new_experiment_results'

CLIENT_COMMAND = 'go run sbbclient.go'



BYTES_PER_MEGABYTE = 2**20
NUM_TRIALS = 5 # number of trials for the experiments
MPC_OPTIONS = ['crypten', 'emp']
BUCKETIZATION_OPTIONS = [True, False]
CLIENT_MATCH_OPTIONS = ['matched', 'not_matched']


def main():
  with open(CONFIG_PATH, "r") as r:
    config = json.load(r)
  for bucketized in BUCKETIZATION_OPTIONS:
    for mpc_option in MPC_OPTIONS:
      for ind in range(NUM_TRIALS):
        for client_match in CLIENT_MATCH_OPTIONS:
          print(f'bucketized: {bucketized}, mpc: {mpc_option}, trial: {ind}, {client_match}')
          config['bucketized'] = bucketized # whether to use SBB
          config['use_secure_sketch'] = False
          config['client_match'] = client_match
          if mpc_option == 'crypten':
            config['use_crypten'] = True
            config['use_emp'] = False
          elif mpc_option == 'emp':
            config['use_crypten'] = False
            config['use_emp'] = True
          else:
            print('Invalid mpc option specified')
          # Make sure the config file is written before running the test
          with open(CONFIG_PATH, 'w') as w:
            json.dump(config, w)
          # Result file will contain the results for this particular trial -- the
          # JSON object output as well as any additional logging/errors
          result_file = '{}/{}_{}_{}_{}_{}'.format(RESULTS_PATH, config['filetype'],
            bucketized, mpc_option, client_match, ind)
          print(f'Printing test results to {result_file}')
          old_num_bytes = psutil.net_io_counters().bytes_sent + psutil.net_io_counters().bytes_recv
          # Note that this will overwrite whatever was at result_file before
          os.system(f'{CLIENT_COMMAND} > {result_file}')
          new_num_bytes = psutil.net_io_counters().bytes_sent + psutil.net_io_counters().bytes_recv
          total_bandwidth = (new_num_bytes - old_num_bytes)/BYTES_PER_MEGABYTE
          print(f'The total bandwidth usage was {total_bandwidth} MiB')
          # Add the bandwidth usage to the result file
          with open(result_file, 'a') as f:
            print(total_bandwidth, file=f)


if __name__ == '__main__':
  main()
