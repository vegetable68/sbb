import os
import json
import torch
import time

import numpy as np
from flask import Flask, Response
from flask import request
from flask import jsonify

from flask import Flask, render_template, request

# Create app
app = Flask(__name__)

now = time.time()
# Load current config
with open('../../config.json', 'r') as r:
  config = json.load(r)

with open(os.path.join(config['filepath'], 'server_data_processed/{}/blocklst_hash_in_bytearray'.format(config['filetype'])), 'r') as r:
    allhashes = json.load(r)
dataset_mtx = torch.load(os.path.join(config['filepath'],
    'server_data_processed/{}/blocklst_hash.pt'.format(config['filetype'])))

with open(os.path.join(config['filepath'], 'server_data_processed/{}/encrypted_hashes.json'.format(config['filetype'])), 'r') as r:
  encrypted_hashes = json.load(r)
print(len(encrypted_hashes))
with open(os.path.join(config['filepath'], 'server_data_processed/{}/blocklst_secure_sketch.json'.format(config['filetype'])), 'r') as r:
  allss = json.load(r)

# Run commands in the background so that the server can send a response
CRYPTEN_COMMAND = ('\"export WORLD_SIZE=2; export RENDEZVOUS=env://;'
                  'export MASTER_ADDR=172.31.26.205; export MASTER_PORT=29500;'
                  ' export RANK=1; source ~/miniconda3/etc/profile.d/conda.sh;'
                  ' (conda activate crypten_env; python ../../mpc_local/launcher.py'
                  ' --bar={} --size={}; conda deactivate) &\"')

EMP_COMMAND = ('\"/home/ubuntu/sbb-implementation/emp-sh2pc/bin/test_example 2 '
  '12345 /tmp/server_bucket {} {} &\"')

def convert2b(settings):

  integerValue = 0
  for idx, setting in enumerate(settings):
    integerValue += int(setting)*2**idx
  # initialize an empty byte
  mybyte = bytearray(b'\x00')
  mybyte[0] = integerValue
  return mybyte

def convert2barray(tmp):
  idx = 0
  mybytes = ''
  while idx < len(tmp):
    mybytes += convert2b(tmp[idx:idx+8]).hex()
    idx += 8
  return mybytes



print("Load Time", time.time() - now)


@app.route('/')
def index():
    resp = Response(response="Success",
         status=200, \
         mimetype="application/json")
    return (resp)

@app.route('/query',  methods=['GET'])
def query():

    now = time.time()
    bucketized = request.args.get('bucketized')
    bucketized = bool(bucketized == 'true')
    use_secure_sketch = request.args.get('use_secure_sketch')
    use_secure_sketch = bool(use_secure_sketch == 'true')
    use_crypten = bool(request.args.get('use_crypten') == 'true')
    use_emp = bool(request.args.get('use_emp') == 'true')
    if bucketized:
      selected_cols = request.args.get('cols')
      cols = []
      ind = 0
      while ind < len(selected_cols):
        cols.append(int(selected_cols[ind:ind+3]))
        ind += 3
      vals = request.args.get('values')
      vals = [True if v == '1' else False for v in vals]
      print(dataset_mtx[:5])
      values = torch.cuda.BoolTensor(vals)
      ret = dataset_mtx[:, cols]
      ret = ret ^ values
      s = torch.sum(ret, 1)
      print(len(s))
      print(s[:50], config['coarse_threshold'])
      idx = torch.where(s < config['coarse_threshold'])[0]
      print(len(idx))
      idx = idx.cpu().tolist()

    if use_secure_sketch:
      if bucketized:
        ret = [allss[ii] for ii in idx]
        encrypted = [encrypted_hashes[ii] for ii in idx]
        res = {'hashes': 'SEPARATOR'.join(ret),
                'encrypted': 'SEPARATOR'.join(encrypted)}
      else:
        res = {'hashes': 'SEPARATOR'.join(allss),
                'encrypted': 'SEPARATOR'.join(encrypted_hashes)}
    else:
      if bucketized:
        ret = [allhashes[ii] for ii in idx]
        res = {'hashes': 'SEPARATOR'.join(ret)}
        # If we're doing just the plaintext protocol then res won't be modified
        if use_crypten:
          with open('/tmp/server_bucket', 'w') as f:
            for phash in ret:
              f.write(phash + '\n')
          full_cmd = CRYPTEN_COMMAND.format(config['threshold'], len(ret))
          print('running command', full_cmd)
          os.system('bash -c ' + full_cmd)
          res = {'bucket_size': len(ret)}
        elif use_emp:
          with open('/tmp/server_bucket', 'w') as f:
            for phash in ret:
              f.write(phash + '\n')
          full_cmd = EMP_COMMAND.format(config['threshold'], len(ret))
          print('running command', full_cmd)
          os.system('bash -c ' + full_cmd)
          res = {'bucket_size': len(ret)}
      else:
          if use_crypten: 
            with open('/tmp/server_bucket', 'w') as f:
              for phash in allhashes:
                f.write(phash + '\n')
            full_cmd = CRYPTEN_COMMAND.format(config['threshold'], len(allhashes))
            print('running command', full_cmd)
            os.system('bash -c ' + full_cmd)
            res = {'bucket_size': len(allhashes)}
          elif use_emp: 
            with open('/tmp/server_bucket', 'w') as f:
              for phash in allhashes:
                f.write(phash + '\n')
            full_cmd = EMP_COMMAND.format(config['threshold'], len(allhashes))
            print('running command', full_cmd)
            os.system('bash -c ' + full_cmd)
            res = {'bucket_size': len(allhashes)}
          else:
            res = {'hashes': 'SEPARATOR'.join(allhashes), 'bucket_size': len(allhashes)}

    if bucketized:
      print("bucket size", len(idx))
    print("query time", time.time() - now)
    resp = Response(response=json.dumps(res),
    status=200, \
    mimetype="application/json")
    return(resp)



if __name__ == '__main__':

    app.run('0.0.0.0', debug=True, port=8080)
