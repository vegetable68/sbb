# Compute aggreagte statistics from the output of the MPC tests
import argparse
import numpy as np
import json

MPC_OPTIONS = ['crypten', 'emp']
#BUCKETIZATION_OPTIONS = [False, True]
BUCKETIZATION_OPTIONS = [True]
MILLISECONDS_PER_SECOND = 1000
CLIENT_MATCH_OPTIONS = ['matched', 'not_matched']


def parse_file(filepath):
    '''
    Given a path to a log file from a test, return the tuple consisting of
    (<latency in seconds>, <bandwidth>)
    '''
    with open(filepath, 'r') as f:
        lines = [line for line in f]
        # The second to last line will contain the JSON result
        result_obj = json.loads(lines[-2])
        # The last line will contain the bandwidth
        bandwidth = float(lines[-1])
        latency_in_seconds = result_obj['client_total_time']/MILLISECONDS_PER_SECOND
        return (latency_in_seconds, bandwidth)

def produce_latex_table_row(stats_dict):
    '''
    Given a dictionary of statistics, will proudce a row for the experimental
    results figure in the paper
    '''
    result = (
        f'$2^{{{stats_dict["bucket_size"]}}}$&$'
        f'{stats_dict["crypten"]["time"]["full"]}'
        f'$&${stats_dict["crypten"]["time"]["sbb"]}$&'
        f'${stats_dict["crypten"]["bandwidth"]["full"]}$&$'
        f'{stats_dict["crypten"]["bandwidth"]["sbb"]}$'
        f'& ${stats_dict["emp"]["time"]["full"]}$&'
        f'${stats_dict["emp"]["time"]["sbb"]}$ & '
        f'${stats_dict["emp"]["bandwidth"]["full"]}$ &'
        f'${stats_dict["emp"]["bandwidth"]["sbb"]}$ \\\\'
    )
    print(result)

def compute_all_stats(results_dir, num_trials, bucketization_options,
    mpc_options, file_type, verbose=False):
    '''
    Computes the average/standard deviation of time (in seconds) and bandwidth
    (in MiB) over the given number of trials and bucketization/mpc options.
    Standard deviation is computed with ddof = 1
    '''
    print(f'Computing statistics for {file_type}')
    stats_dict = {}
    stats_dict["bucket_size"] = file_type[-2:] # last two characters
    for mpc_option in mpc_options:
        stats_dict[mpc_option] = {}
        for metric in ["time", "bandwidth"]:
            stats_dict[mpc_option][metric] = {}

    for mpc_option in mpc_options:
        for bucketized in bucketization_options:
            latency_list = []
            bandwidth_list = []
            for client_match in CLIENT_MATCH_OPTIONS:
                for ind in range(num_trials):
                    result_file = '{}/{}_{}_{}_{}_{}'.format(results_dir, file_type,
                        bucketized, mpc_option, client_match, ind)
                    latency, bandwidth = parse_file(result_file)
                    latency_list.append(latency)
                    bandwidth_list.append(bandwidth)
            bucketization_string = 'bucketized' if bucketized else 'non-bucketized'
            if verbose:
                print(f'Latencies for {bucketization_string} {mpc_option} : {latency_list}')
                print(f'Bandwidths for {bucketization_string} {mpc_option} : {bandwidth_list}')
            mean_latency = np.mean(latency_list)
            stddev_latency = np.std(latency_list, ddof=1)
            mean_bandwidth = np.mean(bandwidth_list)
            stddev_bandwidth = np.std(bandwidth_list, ddof=1)
            result = (
                f'{bucketization_string} {mpc_option}, '
                f'Latency: {mean_latency:.2f} ({stddev_latency:.2f}), '
                f'Bandwidth: {mean_bandwidth:.2f} ({stddev_bandwidth:.2f})'
            )
            if bucketized:
                stats_dict[mpc_option]["time"]["sbb"] =\
                    f'{mean_latency:.2f}({stddev_latency:.2f})'
                stats_dict[mpc_option]["bandwidth"]["sbb"] =\
                    f'{mean_bandwidth:.2f}({stddev_bandwidth:.2f})'
            else:
                stats_dict[mpc_option]["time"]["full"] =\
                    f'{mean_latency:.2f}({stddev_latency:.2f})'
                stats_dict[mpc_option]["bandwidth"]["full"] =\
                    f'{mean_bandwidth:.2f}({stddev_bandwidth:.2f})'
            if len(bucketization_options) == 1: # only bucketized
                stats_dict[mpc_option]["time"]["full"] = '\multicolumn{1}{c}{--}'
                stats_dict[mpc_option]["bandwidth"]["full"] = '\multicolumn{1}{c}{--}'
            print(result)
    produce_latex_table_row(stats_dict)

def main():
    # Handle argument parsing
    parser = argparse.ArgumentParser(description='Stats aggregation script')
    parser.add_argument(
        '--results_dir',
        type=str,
        default='../new_experiment_results',
        help='Directory containing experimental results',
    )

    parser.add_argument(
        '--num_trials',
        type=int,
        default=5,
        help='Directory containing experimental results',
    )

    parser.add_argument(
        '--file_type',
        type=str,
        default='blocklst_2pow18',
        help='The type of blocklist file used',
    )

    args = parser.parse_args()

    compute_all_stats(args.results_dir, args.num_trials, BUCKETIZATION_OPTIONS,
        MPC_OPTIONS, args.file_type)



if __name__ == '__main__':
    main()
