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
      else:
        res = {'hashes': 'SEPARATOR'.join(allhashes)}

    if bucketized:
      print("bucket size", len(idx))
    print("query time", time.time() - now)
    resp = Response(response=json.dumps(res),
    status=200, \
    mimetype="application/json")
    return(resp)



if __name__ == '__main__':

    app.run('0.0.0.0', debug=True, port=8080)
