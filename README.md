# Similarity-based Bucketization (SBB)
An implementation of the SBB system described in *Increasing Adversarial Uncertainty to Scale Private Similarity Testing*.

# SBB implementation 
Two parts, a python web app and a Go web app

## Setup 

### Server Install
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

### Client Install
- Install Go (follow the instruction above)
- go get github.com/steakknife/hamming
- Copy sbb-implementation under $GOPATH/github.com/vegetable68
- cd into sbb-implementation
- Install OPRF go package:
	go get -u github.com/cloudflare/circl@e69048f939ad7a5967c2a6bd8fc548bf5f0519a3
- go get -u github.com/golang/protobuf/proto@v1.4.0

### Download Data
[You need to run aws configure and have an rrg aws account ]
- server: aws s3 cp s3://yiqing-sbb-data/server_data_processed server_data_processed --recursive
- client: aws s3 cp s3://yiqing-sbb-data/client_data_processed client_data_processed --recursive
- change the filepath in config.json according to where you put the data

### Server Deploment 
- Allow [HTTP](https://aws.amazon.com/premiumsupport/knowledge-center/connect-http-https-ec2/) traffic
- Run go run response.go under server/goapp
- Run python app.py under server/deployment

### Client Request
- Change the serverAddr value accordingly
- Run go run sbbclient.go under client
