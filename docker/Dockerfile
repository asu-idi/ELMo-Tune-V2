FROM ubuntu:20.04

ARG TARGETPLATFORM
ARG DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libgflags-dev \
    libsnappy-dev \
    zlib1g-dev \
    libbz2-dev \
    liblz4-dev \
    libzstd-dev \
    cmake \
    git \
    wget \
    fio \
    libjemalloc2 \
    software-properties-common

# Add deadsnakes PPA and install Python 3.10
RUN add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y python3.10 python3.10-distutils python3.10-dev && \
    rm /usr/bin/python3 && ln -s /usr/bin/python3.10 /usr/bin/python3 && \
    wget https://bootstrap.pypa.io/get-pip.py && python3 get-pip.py && rm get-pip.py

# Setup GPT Repo's requirements
ADD requirements.txt /requirements.txt

# Setup Python requirments
RUN pip3 install -r requirements.txt

# Setup RocksDB
RUN wget https://github.com/facebook/rocksdb/archive/refs/tags/v8.8.1.tar.gz && \
    tar -xzf v8.8.1.tar.gz

# Copy modified db_bench and trace_analyzer
COPY db_bench_dynamic_opts/db_bench_tool.cc /rocksdb-8.8.1/tools
COPY db_bench_dynamic_opts/json.hpp /rocksdb-8.8.1/tools
COPY trace_analyzer/tools/trace_analyzer_tool.cc /rocksdb-8.8.1/tools
COPY trace_analyzer/tools/trace_analyzer_tool.h /rocksdb-8.8.1/tools
    
# Compile RocksDB
RUN cd rocksdb-8.8.1 && \
    make -j$(nproc) static_lib db_bench trace_analyzer

# Setup GPT Repo
ADD . /llm-trace-auto-tuning

WORKDIR /llm-trace-auto-tuning
CMD ["python3", "main.py"]
