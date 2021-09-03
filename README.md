# Similarity-based Bucketization (SBB)
An implementation of the SBB system described in *Increasing Adversarial Uncertainty to Scale Private Similarity Testing*.

## SBB implementation with similarity embedding retrieval and secure sketch 
Two parts, a python web app and a Go web app

### Setup 

#### Server Install
- Install [Cuda](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/index.html)
- Install [Anaconda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/linux.html)
- Install Go:
	- wget https://golang.org/dl/go1.15.8.linux-amd64.tar.gz 
	- sudo tar -C /usr/local -xzf go1.15.8.linux-amd64.tar.gz
	- add PATH="$PATH:/usr/local/go/bin" to ~/.bashrc
- Setup [flask](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/create-deploy-python-flask.html)
- Install OPRF go package: 
	go get -u github.com/cloudflare/circl@e69048f939ad7a5967c2a6bd8fc548bf5f0519a3
- Run pip install -r requirements.txt under server
- Copy sbb-implementation under $GOPATH/github.com/vegetable68

#### Client Install
- Install Go (follow the instruction above)
- go get github.com/steakknife/hamming
- Copy sbb-implementation under $GOPATH/github.com/vegetable68
- cd into sbb-implementation
- Install OPRF go package:
	go get -u github.com/cloudflare/circl@e69048f939ad7a5967c2a6bd8fc548bf5f0519a3
- go get -u github.com/golang/protobuf/proto@v1.4.0

#### Download Data
- Preprocess data with scripts under the preprocess folder.

#### Server Deployment 
- Allow [HTTP](https://aws.amazon.com/premiumsupport/knowledge-center/connect-http-https-ec2/) traffic
- Run go run response.go under server/goapp
- Run python app.py under server/deployment

#### Client Request
- Change the serverAddr value accordingly
- Run go run sbbclient.go under client

## MPC Instructions/Info
- Instructions for installing Crypten can be found [here](https://github.com/facebookresearch/CrypTen)
- Instruction for installing EMP can be found [here](https://github.com/emp-toolkit/emp-sh2pc)
- The Crypten MPC logic can be found in `mpc_local/aws_batch_classify.py`
- The EMP logic can be found in `emp/example.cpp`. You have to clone the emp-sh2pc
repo and copy that file to `emp-sh2pc/test/example.cpp`. By default, the command
line program is configured to run locally (for testing purposes). Note that ALICE
is the client and BOB is the server. To run tests across two machines, replace
127.0.0.1 with the IP address of ALICE.
- Correctness tests are in `test_mpc_correctness.py` and are run locally. These
tests can be run by cd-ing into the `mpc_local` directory and running `pytest`.
- In order to run the Crypten and MPC tests for a particular block-list size,
make sure that proper block-list is set in config.json (under `filetype`) and
then run `python mpc_run_expr.py`. This will run the test for all combinations of
(Crypten, MPC) x (bucketized, non-bucketized) x (matched, unmatched) and for
five trials for each possibility. Outputs are written to log files in
`RESULTS_PATH`. Summary statistics can be aggregated using `client/mpc_aggregate_stats.py`
- The MPC routines (for Crypten and EMP) are invoked as sub-processes on the client
and the server. These sub-processes read their input from temp files and write
their output to standard out. The client sends a request to the server that
indicates the MPC type being used (Crypten or EMP) as well as whether bucketization
is being used. The server response indicates the bucket size as this is used in
the MPC protocol (and is leaked anyway through the communication cost of the
protocol).
- The MPC routines XOR the output of the threshold comparison with a random bit
provided by the client. This enables only the client to unblind the result of the
threshold comparison. The result will appear uniformly random to the server
regardless of what the true answer is.
