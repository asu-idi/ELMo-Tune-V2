# ELMo-Tune-V2
This project aims to determine the best configuration for RocksDB using the assistance of LLMs. The process is completely automated, with the user only needing to run their workload.

## Prerequisites
The following instructions are for Ubuntu 20.04 and require Python 3.6 or higher:  

Install dependencies
```bash
apt-get update && apt-get install -y build-essential libgflags-dev libsnappy-dev zlib1g-dev libbz2-dev liblz4-dev libzstd-dev git python3 python3-pip wget fio 
```

Download the ELMo-Tune-V2 and RocksDB repositories:
```bash
git clone https://github.com/asu-idi/ELMo-Tune-V2.git
wget https://github.com/facebook/rocksdb/archive/refs/tags/v8.8.1.tar.gz
tar -xzf v8.8.1.tar.gz
```

Copy modified trace_analyzer and db_bench_tool to RocksDB
```bash
cp ./ELMo-Tune-V2/trace_analyzer/tools/* ./rocksdb-8.8.1/tools/
cp ./ELMo-Tune-V2/db_bench_dynamic_opts/* ./rocksdb-8.8.1/tools/
```

Setup ELMo-Tune-V2
```bash
cd ./ELMo-Tune-V2
pip install -r requirements.txt

cd ../rocksdb-8.8.1
make -j static_lib db_bench trace_analyzer
```

> **Important!!** cgroup_monitor requires root privileges to run. The codebase expects 'llm_cgroup' to be created:
```bash
sudo visudo
```
```bash
# The following gives **all** users the ability to run the root_cgroup_helper.sh script without a password.
ALL ALL=(ALL) NOPASSWD:/path/to/ELMo-Tune-V2/utils/root_cgroup_helper.sh
```
  
## How to use
To run the tests, run the following command:

Go to ELMo-Tune-V2 repo folder
Create `.env` file
```bash
nano .env
```

and put your OpenAI API Key
```.env
OPENAI_API_KEY="sk-..."
```

Make sure the paths in `utils/constant.py` are correctly set for your system.  
Run main.py
```bash
python3 main.py
```

## More Information
- **Contact**: https://asu-idi.github.io/members/zhichao-cao.html
- **About the project**: https://asu-idi.github.io/projects/gpt_project.html
- **ASU IDI Lab**: https://asu-idi.github.io/