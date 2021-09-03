FROM ubuntu:18.04

# Dockerfile for running EMP MPC framework
# Install relevant utilities
# Note that the actually experiments were run in the host OS environment
# and not within a Docker container, however one can test/experiment with
# the code from a Docker container.

RUN apt-get update && \
    apt-get install -y python wget vim tmux sudo


RUN wget https://raw.githubusercontent.com/emp-toolkit/emp-readme/master/scripts/install.py && \
    python install.py -install -tool -sh2pc -ot
