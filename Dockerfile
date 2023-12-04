FROM ubuntu:18.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    redis-server
