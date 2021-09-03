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

filepath = '/data/yiqing/expr_data/'
filetype = 'blocklst_2pow20'

with open(os.path.join(filepath, "{}/client_matched".format(filetype)), "r") as r:
  for line in r:
    data = json.loads(line)
    break

hval = Hash256.fromHexString(data)
s = to_string(hval)

print(s)
#number, pad, rjust, size, kind = data, '0', '>', 256, 'b'
print(format(int(data, 16), '0>256b')[::-1])
#print(f'{number:{pad}{rjust}{size}{kind}}')

