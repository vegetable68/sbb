# This file contains correctenss tests for Crypten and EMP
# These tests are run locally

# Beginning of test utilities
from typing import List
import subprocess

PHASH_LEN= 256 # Length of phash in bits
THRESHOLD = 32 # Threshold for approximate matching
SERVER_BUCKET_SIZE = 7 # Number of phashes in server bucket for test
CLIENT_INPUT_FILE = '/tmp/client_input'
SERVER_INPUT_FILE = 'test_files/server_bucket_test'

def generate_crypten_cmd(client_input: str, server_bucket: str, threshold: int,
    server_bucket_size: int) -> str:
    '''
    Generates the local crypten script invocation with the given parameters.
    '''
    return (
        f'python launcher.py --multiprocess --client_hash_file '
        f'{client_input} --server_hash_file '
        f'{server_bucket} --world_size 2 --bar {threshold} --size {server_bucket_size}'
    )

def generate_emp_cmd(client_input: str, server_bucket: str, threshold: int,
    server_bucket_size: int) -> str:
    '''
    Generates the local emp script invocation with the given parameters
    For emp, make sure the cpp file is properly configured to run locally
    '''
    return (
        f'../emp-sh2pc/bin/test_example 1 12345 {client_input} {threshold} {server_bucket_size} & '
        f'../emp-sh2pc/bin/test_example 2 12345 {server_bucket} {threshold} {server_bucket_size}'
    )

def hex_string_to_bin_string(hex_string: str) -> str:
    '''
    Parameters
    ----------
    hex_string: hex encoded string (without a leading 0x)

    Returns
    -------
    Binary encoded string equivalent of hex_string
    '''
    return format(int(hex_string, 16), f'0{PHASH_LEN}b')

def hamming_dist(a, b):
    '''
    Parameters
    ----------
    a: a binary string
    b: a binary string

    Returns
    -------
    The Hamming distance between a and b
    '''
    assert(len(a) == len(b))
    return sum(1 for i in range(len(a)) if a[i] != b[i] )

def bin_string_to_hex_string(bin_string: str) -> str:
    '''
    Parameters
    ----------
    bin_string: a binary string

    Returns
    -------
    A hex encoded equivalent of `bin_string`

    Notes
    -----
    Reference: https://stackoverflow.com/questions/2072351/python-conversion-from-binary-string-to-hexadecimal
    We splice from index 2 in order to remove the leading "0x"
    '''
    return hex(int(bin_string, 2))[2:]

def flip_string(bin_string: str) -> str:
    '''
    Parameters
    ----------
    bin_string: a binary string

    Returns
    -------
    The string consisting of the bitwise negatino of `bin_string`
    '''
    result = ''
    for c in bin_string:
        if c == '0':
            result += '1'
        elif c == '1':
            result += '0'
        else:
            raise Exception('Invalid string supplied')
    return result


def generate_matched_phash(input_phash: str, threshold: int) -> str:
    '''
    Parameters
    ----------
    input_phash: a hex-encoded phash
    threshold: a threshold for approximate matching

    Returns
    -------
    A phash with hamming distance `threshold - 1` to `input_phash`.
    the output phash is hex-encoded
    '''
    bin_phash = hex_string_to_bin_string(input_phash)
    # Flip the first `threshold - 1` bits of input_phash
    result = flip_string(bin_phash[:threshold - 1]) + bin_phash[threshold - 1:]
    return bin_string_to_hex_string(result)

def generate_unmatched_phash(input_phash: str, threshold: int) -> str:
    '''
    Parameters
    ----------
    input_phash: a hex-encoded phash
    threshold: a threshold for approximate matching

    Returns
    -------
    A phash with hamming distance `threshold` to `input_phash` (the approximate
    matching checks to see if the client hash has Hamming distance < `threshold`
    when compared to any of the server phashes).
    The output phash is hex encoded.
    '''
    bin_phash = hex_string_to_bin_string(input_phash)
    # Flip the first `threshold` bits of input_phash
    result = flip_string(bin_phash[:threshold]) + bin_phash[threshold:]
    return bin_string_to_hex_string(result)

def read_phashes(path: str) -> List[str]:
    '''
    Parameters
    ----------
    path: path to file containing phashes on individual lines

    Returns
    -------
    List of phashes
    '''
    with open(path, 'r') as f:
        return [line.strip() for line in f]

def mpc_test(mpc_framework: str, client_input: str, server_bucket: str,
    threshold: int, server_bucket_size: int) -> bool:
    '''
    Generic MPC test that expects the client phash in test_files/client_hash_test
    and the server bucket in test_files/server_bucket_test

    Inputs
    ------
    mpc_framework: "crypten" or "mpc"
    client_input: path to file containing client phash
    server_bucket: path to file containing server bucket
    threshold: the Hamming distance threshold for approximate matching
    server_bucket_size: the number of phashes in the server bucket

    Returns
    -------
    `True` if `client_input` is within Hamming distance `threshold` to a phash
    contained in `server_bucket`. `False` otherwise.
    '''
    if mpc_framework == 'crypten':
        # TODO: should we dump output to a temp file or capture it somehow?
        crypten_cmd = generate_crypten_cmd(client_input, server_bucket, threshold, server_bucket_size)
        child =  subprocess.run(crypten_cmd, shell=True, capture_output=True, text=True)
        child_output_lines = child.stdout.split('\n')
        result = ''
        for line in child_output_lines:
            tokens = line.split()
            if len(tokens) > 0 and tokens[0] == 'client':
                result = tokens[-1]
        if result == 'True':
            return True
        elif result == 'False':
            return False
        raise Exception('Invalid CrypTen output')
    elif mpc_framework == 'emp':
        emp_cmd = generate_emp_cmd(client_input, server_bucket, threshold, server_bucket_size)
        child = subprocess.run(emp_cmd, shell=True, capture_output=True, text=True)
        child_output_lines = child.stdout.split('\n')
        result = ''
        for line in child_output_lines:
            tokens = line.split()
            if len(tokens) > 0 and tokens[0] == 'actual':
                result = tokens[-1]
        if result == '1':
            return True
        elif result == '0':
            return False
        raise Exception('Invalid EMP output')
    else:
        raise Exception(f'The framework {mpc_framework} is not supported')

# Beginning of tests
# Tests for utility functions
def test_encoding():
    '''
    Test `hex_string_to_bin_string` and `bin_string_to_hex_string`
    '''
    str1_hex = '8969b953363482792fc778b834739f2681bc7053ff4105e630edfa394f54c183'
    str2_bin = format(0b0101010110100100101111000001110101000101000101010100001,
        f'0{PHASH_LEN}b')
    str1_bin = hex_string_to_bin_string(str1_hex)
    str2_hex = bin_string_to_hex_string(str2_bin)
    assert(bin_string_to_hex_string(str1_bin) == str1_hex)
    assert(hex_string_to_bin_string(str2_hex) == str2_bin)

def test_flip_string():
    '''
    Test `flip_string`
    '''
    str1 = '01101'
    str2 = '00000'
    str3 = '11111'
    assert(flip_string(str1) == '10010')
    assert(flip_string(str2) == '11111')
    assert(flip_string(str3) == '00000')

def test_hamming_dist():
    '''
    Tests `hamming_dist`
    '''
    str1 = '01101'
    str2 = '00000'
    str3 = '11111'
    assert(hamming_dist(str1, str2) == 3)
    assert(hamming_dist(str2, str3) == 5)
    assert(hamming_dist(str1, str3) == 2)

def test_gen_phash():
    '''
    Test `generate_matched_phash` and `generate_unmatched_phash`
    '''
    input_phash = '8969b953363482792fc778b834739f2681bc7053ff4105e630edfa394f54c183'
    threshold = 32
    matched = generate_matched_phash(input_phash, threshold)
    unmatched = generate_unmatched_phash(input_phash, threshold)
    bin_matched = hex_string_to_bin_string(matched)
    bin_unmatched = hex_string_to_bin_string(unmatched)
    bin_input_phash = hex_string_to_bin_string(input_phash)
    assert(hamming_dist(bin_input_phash, bin_matched) < threshold)
    assert(hamming_dist(bin_input_phash, bin_unmatched) >= threshold)
    
# Testing MPC
def test_crypten_matched():
    phashes = read_phashes(SERVER_INPUT_FILE)
    matched_phash = generate_matched_phash(phashes[0], THRESHOLD)
    with open(CLIENT_INPUT_FILE, 'w') as f:
        print(matched_phash, file=f)
    assert (mpc_test('crypten', CLIENT_INPUT_FILE, SERVER_INPUT_FILE,
        THRESHOLD, SERVER_BUCKET_SIZE) == True)

def test_crypten_unmatched():
    phashes = read_phashes(SERVER_INPUT_FILE)
    unmatched_phash = generate_unmatched_phash(phashes[0], THRESHOLD)
    with open(CLIENT_INPUT_FILE, 'w') as f:
        print(unmatched_phash, file=f)
    assert (mpc_test('crypten', CLIENT_INPUT_FILE, SERVER_INPUT_FILE,
        THRESHOLD, SERVER_BUCKET_SIZE) == False)

def test_emp_matched():
    phashes = read_phashes(SERVER_INPUT_FILE)
    matched_phash = generate_matched_phash(phashes[0], THRESHOLD)
    with open(CLIENT_INPUT_FILE, 'w') as f:
        print(matched_phash, file=f)
    assert (mpc_test('emp', CLIENT_INPUT_FILE, SERVER_INPUT_FILE,
        THRESHOLD, SERVER_BUCKET_SIZE) == True)

def test_emp_unmatched():
    phashes = read_phashes(SERVER_INPUT_FILE)
    unmatched_phash = generate_unmatched_phash(phashes[0], THRESHOLD)
    with open(CLIENT_INPUT_FILE, 'w') as f:
        print(unmatched_phash, file=f)
    assert (mpc_test('emp', CLIENT_INPUT_FILE, SERVER_INPUT_FILE,
        THRESHOLD, SERVER_BUCKET_SIZE) == False)

