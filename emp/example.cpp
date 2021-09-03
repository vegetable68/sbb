#include "emp-sh2pc/emp-sh2pc.h"

#include <iostream>
#include <fstream>
#include <sstream>
#include <bitset>
#include <string>
#include <vector>
#include <assert.h>
#include <time.h>
using namespace emp;
using namespace std;

const int INT_SIZE = 16;

// Based off of the EMP example

void test_millionare(int party, int number) {
	Integer a(32, number, ALICE);
	Integer b(32, number, BOB);
	Bit res = a > b;

	cout << "ALICE larger?\t"<< res.reveal<bool>()<<endl;
}

vector<int> hex_to_binary(const string& hex_string) {
	//cout << "Calling hex_to_binary" << endl;
	//cout << "hex_string length: " << hex_string.length() << endl;
	assert (hex_string.length() == 64);
	vector<int> result;
	for (unsigned int i = 0; i < hex_string.length(); i++) {
		int n;
		istringstream(hex_string.substr(i, 1)) >> hex >> n;
		bitset<4> bset(n);
		for (unsigned int j = 0; j < bset.size(); j++) {
			result.push_back(bset.test(j) ? 1 : 0);
		}
	}
	//cout << "Done with hex_to_binary" << endl;
	return result;
}

void test_approx_match(int party, char *input_file, int threshold,
		int bucket_size, bool reveal_hamming) {
	assert(bucket_size > 0);
	int size = 256;
	Integer *alice_phash = new Integer[size];
	Integer *bob_phash = new Integer[size * bucket_size];
	//Integer hamming_dist(32, 0, PUBLIC);
	Integer *hamming_dist = new Integer[bucket_size];
	Integer thresh(INT_SIZE, threshold, PUBLIC);
	//int alice_rand = rand() % 2;
	unsigned int random_integer = 0;
	// Read from urandom
	// https://stackoverflow.com/questions/35726331/c-extracting-random-numbers-from-dev-urandom/35727057
	ifstream urand("/dev/urandom", ios::in|ios::binary);
	if (!urand) {
		cout << "urand is not open" << endl;
		assert(0);
	}
	urand.read(reinterpret_cast<char *>(&random_integer), sizeof(unsigned int));
	cout << "The random integer is " << random_integer << endl;
	unsigned int alice_rand = random_integer % 2;
	Bit alice_randomizer(alice_rand, ALICE);


	for (int phash_idx = 0; phash_idx < bucket_size; phash_idx++) {
		hamming_dist[phash_idx] = Integer(INT_SIZE, 0, PUBLIC);
	}

	if (party == ALICE) { // Client
		// Read input from client file
		//cout << "Before ifstream client" << endl;
		//ifstream client_file("/emp-sh2pc/test/client_hash_test");
		ifstream client_file(input_file);
		string line;
		//cout << "Reading client input" << endl;
		getline(client_file, line);
		//string line = "1f031e0010ff087f1fc7f780e700f00f20fce0f83f871f071cf881fbe33b07f8";
		vector<int> result = hex_to_binary(line);
		for (unsigned int i = 0; i < result.size(); i++) {
			alice_phash[i] = Integer(INT_SIZE, result[i], ALICE);
		}
		for (int i = 0; i < size * bucket_size; i++) {
			bob_phash[i] = Integer(INT_SIZE, result[i], BOB);
		}
	} else { // Server
		// Read input from server file
		//cout << "Before ifstream server" << endl;
		//ifstream server_file("/emp-sh2pc/test/server_bucket_test");
		ifstream server_file(input_file);
		string line;
		//cout << "Reading server input" << endl;
		int phash_idx = 0;
		while (getline(server_file, line)) {
			if (phash_idx == bucket_size) {
				break;
			}
			vector<int> result = hex_to_binary(line);
			for (unsigned int i = 0; i < result.size(); i++) {
				bob_phash[phash_idx * size + i] = Integer(INT_SIZE, result[i], BOB);
			}
			phash_idx++;
		}
		//string line = "1f031e0010ff087f1fc7f780e700f00f20fce0f83f871f071cf881fbe33b07f8";
		for (int i = 0; i < size; i++) {
			alice_phash[i] = Integer(INT_SIZE, 0, ALICE);
		}
	}

	//cout << "Made it past reading input" << endl;


	// compute hamming distance;
	for (int phash_idx = 0; phash_idx < bucket_size; phash_idx++) {
		for (int i = 0; i < size; i++) {
			hamming_dist[phash_idx] = hamming_dist[phash_idx] + (alice_phash[i] ^ bob_phash[phash_idx * size + i]);
		}
	}

	if (reveal_hamming) {
		for (int phash_idx = 0; phash_idx < bucket_size; phash_idx++) {
			cout << "hamming dist " << hamming_dist[phash_idx].reveal<int32_t>() << endl;
		}
	} else {
		Bit result = hamming_dist[0] < thresh;
		for (int phash_idx = 1; phash_idx < bucket_size; phash_idx++) {
			// TODO: check that this is OR
			result = result | (hamming_dist[phash_idx] < thresh);
		}
		bool obfuscated_result = (result ^ alice_randomizer).reveal<bool>();
		cout << "obfuscated result: " << obfuscated_result << endl;
		if (party == ALICE) {
			if (alice_rand == 1) {
				cout << "actual result " << !obfuscated_result << endl;
			} else {
				cout << "actual result " << obfuscated_result << endl;
			}
		}
		//cout << "phash approximate match: " << result.reveal<bool>() << endl;

	}
	cout << "test rand " << rand() << endl;
	//Bit res = hamming_dist <= thresh;

	//cout << "Approx match?\t" << res.reveal<bool>() << endl;


	delete [] alice_phash;
	delete [] bob_phash;
	delete [] hamming_dist;
}

void test_sort(int party) {
	int size = 100;
	Integer *A = new Integer[size];
	Integer *B = new Integer[size];
	Integer *res = new Integer[size];

// First specify Alice's input
	for(int i = 0; i < size; ++i)
		A[i] = Integer(32, rand()%102400, ALICE);


// Now specify Bob's input
	for(int i = 0; i < size; ++i)
		B[i] = Integer(32, rand()%102400, BOB);

//Now compute
	for(int i = 0; i < size; ++i)
		res[i] = A[i] ^ B[i];


	sort(res, size);
	for(int i = 0; i < 100; ++i)
		cout << res[i].reveal<int32_t>()<<endl;

	delete[] A;
	delete[] B;
	delete[] res;
}

int main(int argc, char** argv) {
	int port, party;
	parse_party_and_port(argv, &party, &port);
	if (party == ALICE) {
		cout << "Alice is party " << party << endl;
	} else {
		cout << "Bob is party " << party << endl;
	}
 	char *input_file = NULL; // contains either client hash or server bucket
	int threshold = 0; // threshold for approximate comparison
	int bucket_size = 0;
	//srand (time(NULL));
	// ./bin/test_example <party> <port> <input-file> <threshold> <bucket-size>
	if(argc > 5) {
		input_file = argv[3];
		threshold = atoi(argv[4]);
		bucket_size = atoi(argv[5]);
	} else {
		cout << "Invalid command line arguments" << endl;
		return 1;
	}
	// NetIO * io = new NetIO(party==ALICE ? nullptr : "172.31.26.205", port);
	NetIO * io = new NetIO(party==ALICE ? nullptr : "127.0.0.1", port);

	setup_semi_honest(io, party);
	test_approx_match(party, input_file, threshold, bucket_size, false);
	cout << CircuitExecution::circ_exec->num_and()<<endl;
	finalize_semi_honest();
	cout << "The number of bytes sent was " << io->counter << endl;
	delete io;
}