import torch
from third_party.pdqhashing.types.hash256 import Hash256
import json
import random
import time
import os
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

def get_poly(m, r):
  if m == 0:
    return [[]]
  ret = []
  tmp = get_poly(m-1, r)
  for t in tmp:
    ret.append([0] + t)
  if r > 0:
    tmp = get_poly(m-1, r-1)
    for t in tmp:
      ret.append([1] + t)
  return ret

polymtx = get_poly(M, R)
polymtx = [x[::-1] for x in polymtx]

masks = []
for _ in range(R+1):
  masks.append([])
for ind, vec in enumerate(polymtx):
  s = np.sum(vec)
  masks[s].append(ind)
    
def get_value(x, vec, m):
  xind = 0
  ret = 0
  for ind in range(m):
    if (vec[ind] == 0):
      ret = ret + ((x % 2)<<(xind))
      xind += 1
    x = (x>>1)
  return ret

b = np.zeros((K, 2**M, 2**M))
for ind, vec in enumerate(polymtx):
  t = np.sum(vec)
  mm = 0
  for col, x in enumerate(range(2**M)):
    row = get_value(x, vec, M)
    b[ind][row][col] = 1 
    if row > mm:
      mm = row
b = torch.cuda.FloatTensor(b) # k * n * n

def convert2b(settings):

  integerValue = 0
  # init value of your settings
  for idx, setting in enumerate(settings):
    integerValue += int(setting)*2**idx
  # initialize an empty byte
  mybyte = bytearray(b'\x00')
  mybyte[0] =integerValue
  return mybyte

def convert2b_with_int(settings):

  integerValue = 0
  # init value of your settings
  for idx, setting in enumerate(settings):
    integerValue += int(setting)*2**idx
  # initialize an empty byte
  mybyte = bytearray(b'\x00')
  mybyte[0] =integerValue
  return mybyte, integerValue

def convert2barray(tmp):
  idx = 0
  mybytes = []
  while idx < len(tmp):
    mybytes.append(convert2b(tmp[idx:idx+8]).hex())
    idx += 8
  return ''.join(mybytes)

def convert2barray_with_more_info(tmp):
  idx = 0
  mybytes = []
  cols = []
  while idx < len(tmp):
    byt, i = convert2b_with_int(tmp[idx:idx+8])
    mybytes.append(byt.hex())
    if i > 0:
        cols.append(int(idx / 8))
    idx += 8
  return ''.join(mybytes), cols

#b = b.cpu().tolist()
b_in_bytes = []
b_entries_with_one = []
for xx in b:
  cur = []
  entries_with_one = []
  for row in xx:
    byt, cols = convert2barray_with_more_info(row)
    cur.append(byt)
    entries_with_one.append(','.join([str(c) for c in cols]))
  b_entries_with_one.append('.'.join(entries_with_one))
  b_in_bytes.append(','.join(cur))

Gen_t = torch.t(Gen)
Gen_t = Gen_t.cpu().tolist()
gen_t_in_bytes = []
for row in Gen_t:
  gen_t_in_bytes.append(convert2barray(row))
gen_t_in_bytes = ','.join(gen_t_in_bytes)

# bitcount
def count(b):
  cnt = 0
  idx = 128
  while idx > 0:
    if (b&idx) > 0:
      cnt += 1
    idx = (idx >>1)
  return cnt
bitcount = {}
for x in range(256):
  bitcount[x] = count(x)

dump_data = {'gen_t': gen_t_in_bytes, 'mtx_b': b_in_bytes, 'masks': masks, 'bitcount': bitcount,
            'mtx_b_aux': b_entries_with_one}
filepath = '/data/yiqing/expr_data/'

with open(os.path.join(filepath, "client_side_secure_sketch_{}_{}.json".format(
    M, R)), "w") as w:
  json.dump(dump_data, w)

def to_string(h):
  ret = ''

  for wind in range(15,-1, -1):
    rec = 0
    last = 0
    for bitind in range(15,-1,-1):
      cur = (h.w[wind] - last)>>bitind
      last = (h.w[wind]>>bitind)<<bitind
      rec += (cur<<bitind)
      ret = ret + str(cur)
    assert(rec==h.w[wind])
  ret = ret[::-1]
  return ret


def get_client_data(filetype):

  L = 256
  filepath = '/data/yiqing/expr_data/'

  dataset_mtx = []
  hash_repeats = []
  with open(os.path.join(filepath, "{}/client_matched".format(filetype)), "r") as r:
    for line in r:
      hash_repeats.append(json.loads(line))
  print(len(hash_repeats))

  ind=0
  cnts = []
  data = []
  data_in_bytes = []
  for h in hash_repeats:
    hval = Hash256.fromHexString(h)
    s = to_string(hval)
    data.append(s)
    data_in_bytes.append(convert2barray(s))
    
  with open(os.path.join(filepath, "client_data_processed/{}/client_matched_data_as_strings.json".format(filetype)), "w") as w:
      json.dump(data, w)
  with open(os.path.join(filepath, "client_data_processed/{}/client_matched_data_as_bytes.json".format(filetype)), "w") as w:
      json.dump(data_in_bytes, w)

  dataset_mtx = []
  hash_repeats = []
  with open(os.path.join(filepath, "{}/client_not_matched".format(filetype)), "r") as r:
    for line in r:
      hash_repeats.append(json.loads(line))
  print(len(hash_repeats))

  ind=0
  data = []
  data_in_bytes = []
  for h in hash_repeats:
    hval = Hash256.fromHexString(h)
    s = to_string(hval)
    data.append(s)
    data_in_bytes.append(convert2barray(s))
    
  with open(os.path.join(filepath, "client_data_processed/{}/client_not_matched_data_as_strings.json".format(filetype)), "w") as w:
      json.dump(data, w)
  with open(os.path.join(filepath, "client_data_processed/{}/client_not_matched_data_as_bytes.json".format(filetype)), "w") as w:
      json.dump(data_in_bytes, w)




for filename in  ['blocklst_2pow13', 'blocklst_2pow14', 'blocklst_2pow15', 'blocklst_2pow16', 'blocklst_2pow17']:
  get_client_data(filename)

