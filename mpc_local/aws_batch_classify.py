import crypten
import torch
import random
import time
#import psutil
import numpy as np
import secrets
NUM=256
BAD_LIST=250000
alpha=0.01

# The rank of the client respectively, required for launching CrypTen Processes
SERVER = 1
CLIENT = 0

PHASH_LEN= 256 # Length of phash in bits
INT_SIZE = 64 # Length of (torch) integer in bits
HEX_DIGITS_PER_INT = 16 # the number of hex digits within INT_SIZE
PACKED_TENSOR_LEN = 4 # Length of a bit-packed tensor

def write_bytes(filename,number):
    lst=[]
    for i in range(number):
        number=random.randint(0,2**256-1)
        lst.append(hex(number)[2:])
    with open(filename,"w") as f:
        for i in lst:
            f.write(i+"\n")

def read_hex_into_bin(filename):
    strings=[]
    lst=[]
    with open(filename,"r")as f:
        strings=f.readlines()
    for i in strings:
        bits= bin(int(i, 16))[2:].zfill(NUM)
        lst.append([int(x) for x in bits])
    # for client hash, we want (NUM,) instead of (1,NUM)
    return torch.squeeze(torch.tensor(lst))

def pack_bits_into_single_int(hex_bits):
    """
    hex_bits: Provided as a hex-encoded string of length HEX_DIGITS_PER_INT
    which is INT_SIZE/4 since there are 4 bits per hex digit.
    Returns the signed 64 bit integer corresponding to the hex_bits
    """
    assert(len(hex_bits) == HEX_DIGITS_PER_INT)
    return int.from_bytes(bytearray.fromhex(hex_bits), byteorder='little', signed=True)

def read_hex_into_bin_pack_bits(filename, rank):
    """
    A version of read_hex_into_bin that will pack bits into little-endian
    torch.int64 values.
    """
    with open(filename, 'r') as f:
        phash_list = []
        for hex_line in f:
            hex_line = hex_line.replace('\"', '').strip() # take off the quotes
            assert (len(hex_line) == HEX_DIGITS_PER_INT * 4)
            curr_phash = []
            for i in range(PHASH_LEN//INT_SIZE):
                start, end = HEX_DIGITS_PER_INT * i, HEX_DIGITS_PER_INT * (i + 1)
                curr_phash.append(pack_bits_into_single_int(hex_line[start: end]))
            phash_list.append(curr_phash)
    if rank == CLIENT: # read in a single hash
        assert(len(phash_list) == 1)
        return torch.tensor(phash_list[0], dtype=torch.int64)
    elif rank == SERVER: # read multiple hashes into a tensor
        return torch.tensor(phash_list, dtype=torch.int64)
    else:
        raise Exception('rank must be CLIENT or SERVER')




def hamming_weight_packed(row_xor):
    """
    row_and: tensor with rows of length PACKED_TENSOR_LEN
    Returns a tensor whoses elements are the hamming weight of each row

    """
    result = []
    weights = torch.zeros(row_xor.size(), dtype=torch.int64)
    for j in range(INT_SIZE):
        weights += (torch.full(row_xor.size(), 1,
            dtype=torch.int64) & (row_xor >> j)).to(crypten.ptype.arithmetic)
    print('weights', weights)
    
    return weights.sum(1) # sum 


def classify_packed_bits(thresh, bucket_size, client_hash_file, server_hash_file, reveal_hamming=False):
    # TODO: check if having the correct bucket size is important here
    rank = crypten.communicator.get().get_rank()
    if rank == CLIENT:
        client_hash_pt =read_hex_into_bin_pack_bits(client_hash_file, rank)
        print('client tensor shape', client_hash_pt.size())
        batch_hash_pt = torch.empty(bucket_size, PACKED_TENSOR_LEN)
    else:
        client_hash_pt =torch.empty(PACKED_TENSOR_LEN,)
        batch_hash_pt =read_hex_into_bin_pack_bits(server_hash_file, rank)
        print('server tensor shape', batch_hash_pt.size())

    client_hash = crypten.cryptensor(client_hash_pt, src=CLIENT,
        ptype=crypten.ptype.binary)
    sbb_bucket = crypten.cryptensor(batch_hash_pt, src=SERVER,
        ptype=crypten.ptype.binary)

    row_xor  = client_hash ^ sbb_bucket
    row_hamming = hamming_weight_packed(row_xor)

    if reveal_hamming: # for debugging purposes
        print('row hammming weights', row_hamming.get_plain_text())

    flag = (row_hamming <= thresh).sum() # TODO: check if < or <=
    result=int((flag>0).get_plain_text().item())

    if rank==CLIENT:
        print(bool(result))
    
def classify(bar, size, client_hash_file, server_hash_file, reveal_hamming=False):
    crypten.init()
    rank = crypten.communicator.get().get_rank()
    crypten.communicator.get().set_verbosity(True)
    # client hash generation
    if rank == CLIENT:
        client_hash = read_hex_into_bin(client_hash_file)
        batch_hash = torch.empty(size, PHASH_LEN)
        client_rand = torch.tensor([secrets.choice([-1, 1])]) # client randomizer
    else:
        client_hash = torch.empty(PHASH_LEN,)
        batch_hash = read_hex_into_bin(server_hash_file)
        client_rand = torch.tensor([1])

    client = crypten.cryptensor(client_hash,src=CLIENT)
    batch = crypten.cryptensor(batch_hash,src=SERVER)
    client_randomizer = crypten.cryptensor(client_rand, src=CLIENT)

    #hamming distance
    row_norm = (batch-client).norm(p=1,dim=1)
    if reveal_hamming:
        print(row_norm.get_plain_text())
    # flag would be a positive integer if at least one is within bar
    flag = (row_norm < bar).sum() > 0
    # x -> 1 - 2x takes us from (1, 0) -> (-1, 1)
    obfuscated_result = ((1 - 2 * flag) * client_randomizer).get_plain_text().item()
    print('obfuscated result', obfuscated_result)
    # result = int((flag>0).get_plain_text().item())

    if rank == CLIENT:
        # print(bool(result))
        # x -> (1 - x)/2 takes us from (-1, 1) -> (1, 0)
        result = (1 - obfuscated_result * client_rand)/2
        print('client result', bool(result))
    crypten.print_communication_stats()
    comm = crypten.communicator.get()
    print('rounds', comm.comm_rounds, 'bytes', comm.comm_bytes)
