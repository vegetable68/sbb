import json
import os
import subprocess
import time
import psutil

with open("../config.json", "r") as r:
  config = json.load(r)


def convert_to_kb(value):
  return value/1024.

def send_stat(value):
  return convert_to_kb(value)


for use_secure_sketch in [False, True]:
  for bucketized in [True, False]:
    if bucketized == False:
      continue
    if use_secure_sketch == True and bucketized == False:
      continue
    if use_secure_sketch == True:
      indrange = 5
    else:
      indrange = 15
    for client_match in ['matched', 'not_matched']:
      for ind in range(indrange):
        print(bucketized, client_match, use_secure_sketch)
        config['bucketized'] = bucketized
        config['use_secure_sketch'] = use_secure_sketch
        config['client_match'] = client_match
        with open("../config.json", "w") as w:
          json.dump(config, w)

        filename = "{}_{}_{}_{}_{}".format(config['filetype'],
           bucketized, use_secure_sketch, client_match, ind) 


        old_value = psutil.net_io_counters().bytes_sent + psutil.net_io_counters().bytes_recv
        os.system("go run sbbclient.go > ../expr_res/{}".format(filename))      
        time.sleep(1)

        new_value = psutil.net_io_counters().bytes_sent + psutil.net_io_counters().bytes_recv
        with open("../expr_res/{}".format(filename), "r") as r:
          data = json.load(r)
        data['total_bandwidth'] = send_stat(new_value - old_value)
        with open("../expr_res/{}".format(filename), "w") as w:
          json.dump(data, w)
