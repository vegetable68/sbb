# A plaintext comparison for sanity check

import argparse
from aws_batch_classify import PHASH_LEN


def hex_string_to_bin_string(hex_string):
    '''
    Converts a hex encoded string (without a leading 0x) to a binary encoded
    string
    '''
    return format(int(hex_string, 16), f'0{PHASH_LEN}b')

def hamming_dist(a, b):
    '''
    Accepts two binary strings as input
    '''
    assert(len(a) == len(b))
    return sum(1 for i in range(len(a)) if a[i] != b[i] )

def main():
    parser = argparse.ArgumentParser(description="Plaintext test")
    parser.add_argument(
        "--client_hash",
        type=str,
        default='test_files/client_hash_test',
        help="Client supplied phash file",
    )

    parser.add_argument(
        "--server_bucket",
        type=str,
        default='test_files/server_bucket_test',
        help="Client supplied phash",
    )
    args = parser.parse_args()

    with open(args.client_hash, 'r') as client, open(args.server_bucket, 'r') as server:
        client_hash = ''
        for line in client:
            client_hash = hex_string_to_bin_string(line)
        for server_hash in server:
            print(hamming_dist(client_hash, hex_string_to_bin_string(server_hash)))



if __name__ == '__main__':
    main()