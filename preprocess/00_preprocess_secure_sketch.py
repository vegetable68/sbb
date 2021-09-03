import torch
import os
from third_party.pdqhashing.types.hash256 import Hash256
import json
import random
import time
import numpy as np
import operator as op
from functools import reduce

from ctypes import *

# define parameters

EMBED_LEN = 13
COARSE_THRESHOLD = 2
FLIP_BIAS = 0.05

# Reed-Muller parameters
M = 8
R = 3

def ncr(n, r):
    r = min(r, n-r)
    numer = reduce(op.mul, range(n, n-r, -1), 1)
    denom = reduce(op.mul, range(1, r+1), 1)
    return numer / denom


K = 0
for x in range(R+1):
  K += ncr(M, x)
K = int(K)

def get_RM_genarator_matrix(m, r):
  if m == r:
    if G[m-1][r-1] is None:
      G[m-1][r-1] = get_RM_genarator_matrix(m-1, r-1)
    ret = torch.cat([G[m-1][r-1], G[m-1][r-1]], 1)
    lower = torch.cat([torch.zeros([G[m-1][r-1].shape[0], 
                                    G[m-1][r-1].shape[1]]),
                       G[m-1][r-1]], 1)
    ret = torch.cat([ret, lower], 0)
    return ret
  if r == 1:
    if G[m-1][1] is None:
      G[m-1][1] = get_RM_genarator_matrix(m-1, 1)
    colsize = G[m-1][1].shape[1]
    last_row = torch.cat([torch.zeros([1, colsize]), torch.ones([1, colsize])], 1)
    ret = torch.cat([G[m-1][1], G[m-1][1]], 1)
    ret = torch.cat([ret, last_row], 0)
    return ret
  if G[m-1][r] is None:
    G[m-1][r] = get_RM_genarator_matrix(m-1, r)
  if G[m-1][r-1] is None:
    G[m-1][r-1] = get_RM_genarator_matrix(m-1, r-1)
  upper = torch.cat([G[m-1][r], G[m-1][r]], 1)
  lower = torch.cat([torch.zeros([G[m-1][r-1].shape[0], G[m-1][r].shape[1]]), G[m-1][r-1]], 1)
  ret = torch.cat([upper, lower], 0)
  return ret

G = []
for x in range(M+1):
  cur = []
  for y in range(M+1):
    cur.append(None)
  G.append(cur)
G[1][1] = torch.tensor([[1., 1.], [0., 1.]])

Gen = get_RM_genarator_matrix(M, R)
Gen = Gen.to(device='cuda')


# Load dataset



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


def get_data_mtx(filetype):

  L = 256

  dataset_mtx = []
  hash_repeats = []
  with open(os.path.join(filepath, "{}/server".format(filetype)), "r") as r:
    for line in r:
      data = json.loads(line) 
      hash_repeats.append(data)
      if data is None:
        print(line)

  print(len(hash_repeats))
  hash_repeats = set(hash_repeats)
  print(len(hash_repeats))

  ind=0
  for h in hash_repeats:
    hval = format(int(h, 16), '0>256b')[::-1]
    dataset_mtx.append([True if hh == '1' else False for hh in hval])

  dataset_mtx = torch.cuda.BoolTensor(dataset_mtx)

  
  totallen = dataset_mtx.shape[0]
  batch = 2**5
  if totallen > batch:
    secure_hash_dataset_mtx = []
    random_genarators = []
    ind = 0
    while ind < totallen:
      torch.cuda.empty_cache()
      random_genarator = torch.randint(0, 2, (batch, Gen.shape[0])).float()
      random_genarator = random_genarator.to(device='cuda')
      random_codewords = torch.fmod(torch.mm(random_genarator, Gen), 2).bool()
      secure_hash_dataset_mtx.append(dataset_mtx[ind:ind+batch, :] ^ random_codewords)
      random_genarators.append(random_genarator)
      ind += batch
    secure_hash_dataset_mtx = [ss for s in secure_hash_dataset_mtx for ss in s.cpu().tolist()]
    random_genarators = [ss for s in random_genarators for ss in s.cpu().tolist()]
  else:
    # Generate random generators for the server
    random_genarators = torch.randint(0, 2, (dataset_mtx.shape[0], Gen.shape[0])).float()
    random_genarators = random_genarators.to(device='cuda')
    random_codewords = torch.fmod(torch.mm(random_genarators, Gen), 2).bool()
    secure_hash_dataset_mtx = dataset_mtx ^ random_codewords

  # save the preprocessed value

  torch.save(dataset_mtx, os.path.join(filepath, "server_data_processed/{}/blocklst_hash.pt".format(filetype)))
  allhashes = []
  for h in dataset_mtx.cpu().tolist():
    allhashes.append(convert2barray(h))
  with open(os.path.join(filepath, "server_data_processed/{}/blocklst_hash_in_bytearray".format(filetype)), "w") as w:
    json.dump(allhashes, w)
  allss = []
  for h in secure_hash_dataset_mtx:
    allss.append(convert2barray(h))
  with open(os.path.join(filepath, "server_data_processed/{}/blocklst_secure_sketch.json".format(filetype)), "w") as w:
    json.dump(allss, w)  
  output = ["".join([str(int(r)) for r in row]) for row in random_genarators]
  with open(os.path.join(filepath, "server_data_processed/{}/random_generator.json".format(filetype)), "w") as w:
      json.dump(output, w)

filepath = "/data/yiqing/expr_data/"
for filetype in  ['blocklst_2pow13', 'blocklst_2pow14', 'blocklst_2pow15', 'blocklst_2pow16', 'blocklst_2pow17']:
  get_data_mtx(filetype) 
