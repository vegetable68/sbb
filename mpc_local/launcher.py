#!/usr/bin/env python3

# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.


import argparse
import logging
import os
import crypten

import time
#crypten.init()

from examples.multiprocess_launcher import MultiProcessLauncher
from aws_batch_classify import *

parser = argparse.ArgumentParser(description="CrypTen Private Threshold Comparison")

parser.add_argument(
    "--multiprocess",
    default=False,
    action="store_true",
    help="Run example in multiprocess mode",
)

parser.add_argument(
    "--bit_packing",
    default=False,
    action="store_true",
    help="Use bit packing in protocol",
)

parser.add_argument(
    "--reveal_hamming",
    default=False,
    action="store_true",
    help="Reveal hamming distances for debugging purposes",
)

parser.add_argument(
    "--world_size",
    type=int,
    default=2,
    help="The number of parties to launch. Each party acts as its own process",
)

parser.add_argument(
    "--bar",
    type=int,
    default=3,
    help="approximiate matching bar for tensor",
)

parser.add_argument(
    "--size",
    type=int,
    default=7,
    help="bucket size",
)

parser.add_argument(
    "--client_hash_file",
    type=str,
    default="/tmp/client_hash",
    help="file containing client phash",
)

parser.add_argument(
    "--server_hash_file",
    type=str,
    default="/tmp/server_bucket",
    help="file containing server bucket",
)



def _run_experiment(args):
    level = logging.INFO
    #reserved for potential tcp communication
    #ips=os.environ["ips"].split(",")
    #dns=os.environ["dns"].split(",")
    #remote_dns=dns[1-int(os.environ["RANK"])]
    if "RANK" in os.environ and os.environ["RANK"] != "0":
        level = logging.CRITICAL
    logging.getLogger().setLevel(level)
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(process)d - %(name)s - %(levelname)s - %(message)s",
    )

    print('Running classify')
    # print('bit_packing', args.bit_packing)
    # print(crypten.communicator.comm_bytes)
    if args.bit_packing:
        print('Running protocol with bit-packing')
        classify_packed_bits(args.bar, args.size, args.client_hash_file,
        args.server_hash_file, args.reveal_hamming)
    else:
        classify(args.bar,args.size, args.client_hash_file,
        args.server_hash_file, args.reveal_hamming)

def main(run_experiment):
    args = parser.parse_args()
    if args.multiprocess:
        launcher = MultiProcessLauncher(args.world_size, run_experiment, args)
        launcher.start()
        launcher.join()
        launcher.terminate()
    else:
        # crypten.reset_communication_stats()
        run_experiment(args)


if __name__ == "__main__":
    main(_run_experiment)
