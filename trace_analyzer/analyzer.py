import os
import subprocess
from utils.utils import log_update
from utils.constants import TRACE_ANALYZER_PATH, OUTPUT_PATH
from trace_analyzer.trace_converter import convert_txt_to_csv, convert_txt_to_csv_windows
from trace_analyzer.trace_summarizer import generate_summary, generate_summary_windows, generate_summary_row
import base64
from gpt.gpt_request import send_gpt_request
import re
import json
import pandas as pd


def analyze_tracefile(tracefile_path):
    '''
    Function to create a workload summary from tracefile.

    Parameters:
    - tracefile_path (str): The path of tracefile

    Returns:
    - A workload summary from tracefile.
    '''

    # Convert ml_feature.txt or ml_feature_windows.txt to ml_feature.csv
    output_csv = f"{OUTPUT_PATH}/trace_data/ml_feature.csv"
    output_csv_windows = f"{OUTPUT_PATH}/trace_data/ml_feature_windows.csv"

    input_txt = f"{OUTPUT_PATH}/trace_data/ml_feature.txt"
    input_txt_windows = f"{OUTPUT_PATH}/trace_data/ml_feature_windows.txt"

    # If ml_feature.csv doesn't exist, run trace analyzer
    if ((not (os.path.exists(output_csv) and (os.path.getsize(output_csv) != 0))) or 
        not (os.path.exists(output_csv_windows) and (os.path.getsize(output_csv_windows) != 0))):
        
        # Create trace data folder
        os.makedirs(f"{OUTPUT_PATH}/trace_data", exist_ok=True)

        command = [
            TRACE_ANALYZER_PATH,
            "-analyze_get",
            "-analyze_put",
            "-analyze_delete",
            "-analyze_iterator",
            "-analyze_merge",
            "-analyze_multiget",
            "-analyze_range_delete",
            "-analyze_single_delete",
            f"-key_space_dir={OUTPUT_PATH}/trace_data",
            f"-output_dir={OUTPUT_PATH}/trace_data",
            # "-convert_to_human_readable_trace",
            "-output_ml_features_windows",
            "-output_ml_features_windows_size=10",
            "-output_key_distribution",
            "-output_access_count_stats",
            # "-output_key_stats",
            # "-output_qps_stats",
            "-output_value_distribution",
            # "-print_overall_stats",
            # "-print_top_k_access=5",
            # "-sample_ratio=0.1",
            # "-output_ml_features",
            f"-trace_path={tracefile_path}"
        ]

        log_update("[TAL] Run trace_analyzer")
        print("[TAL] Run trace_analyzer")

        proc_out = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False
        )

        log_update("[TAL] Finish analyze tracefile")
        print("[TAL] Finish analyze tracefile")

        if proc_out.returncode != 0:
            log_update(f"[TAL] Trace Analyzer error occurred. Output:\n{proc_out.stdout.decode()}")
            print(f"[TAL] Trace Analyzer error occurred. Output:\n{proc_out.stdout.decode()}")
            exit(1)

        # Write output log to the qlt.txt
        with open(f"{OUTPUT_PATH}/trace_data/qlt.txt", "w") as of:
            of.write(proc_out.stdout.decode())

        if os.path.exists(input_txt_windows):
            convert_txt_to_csv_windows(input_txt_windows, output_csv_windows)
        elif os.path.exists(input_txt):
            convert_txt_to_csv(input_txt, output_csv)
        else:
            raise FileNotFoundError("Neither 'ml_feature_windows.txt' nor 'ml_feature.txt' was found.")

    if os.path.exists(input_txt_windows):
        trace_result = generate_summary_windows(f"{OUTPUT_PATH}/trace_data/ml_feature_windows.csv")
    else:
        # Create summary trace text
        trace_result = generate_summary(f"{OUTPUT_PATH}/trace_data/ml_feature.csv")

    return trace_result

def analyze_last_n_tracefile_windows(tracefile_path, n=2):
    # Create trace data folder
    os.makedirs(f"{OUTPUT_PATH}/trace_data_dyn", exist_ok=True)

    command = [
        TRACE_ANALYZER_PATH,
        "-analyze_get",
        "-analyze_put",
        "-analyze_delete",
        "-analyze_iterator",
        "-analyze_merge",
        "-analyze_multiget",
        "-analyze_range_delete",
        "-analyze_single_delete",
        f"-key_space_dir={OUTPUT_PATH}/trace_data_dyn",
        f"-output_dir={OUTPUT_PATH}/trace_data_dyn",
        # "-convert_to_human_readable_trace",
        "-output_ml_features_windows",
        "-output_ml_features_windows_size=10",
        # "-output_key_distribution",
        # "-output_access_count_stats",
        # "-output_key_stats",
        # "-output_qps_stats",
        # "-output_value_distribution",
        # "-print_overall_stats",
        # "-print_top_k_access=5",
        "-sample_ratio=0.01",
        # "-output_ml_features",
        f"-trace_path={tracefile_path}"
    ]

    log_update(f"[TAL] Run trace_analyzer for last {n} lines of tracefile")
    print(f"[TAL] Run trace_analyzer for last {n} lines of tracefile")

    proc_out = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False
    )

    log_update(f"[TAL] Finish analyze last {n} lines of tracefile")
    print(f"[TAL] Finish analyze last {n} lines of tracefile")

    if proc_out.returncode != 0:
        log_update(f"[TAL] Trace Analyzer error occurred. Output:\n{proc_out.stdout.decode()}")
        print(f"[TAL] Trace Analyzer error occurred. Output:\n{proc_out.stdout.decode()}")
        exit(1)

    # Write output log to the qlt.txt
    with open(f"{OUTPUT_PATH}/trace_data_dyn/qlt.txt", "w") as of:
        of.write(proc_out.stdout.decode())
    
    # Convert ml_feature.txt or ml_feature_windows.txt to ml_feature.csv
    output_csv = f"{OUTPUT_PATH}/trace_data_dyn/ml_feature.csv"
    output_csv_windows = f"{OUTPUT_PATH}/trace_data_dyn/ml_feature_windows.csv"

    input_txt = f"{OUTPUT_PATH}/trace_data_dyn/ml_feature.txt"
    input_txt_windows = f"{OUTPUT_PATH}/trace_data_dyn/ml_feature_windows.txt"

    if os.path.exists(input_txt_windows):
        convert_txt_to_csv_windows(input_txt_windows, output_csv_windows)
    elif os.path.exists(input_txt):
        convert_txt_to_csv(input_txt, output_csv)
    else:
        raise FileNotFoundError("Neither 'ml_feature_windows.txt' nor 'ml_feature.txt' was found.")

    trace_result_summary = ["The workload information is as follows:\n"]
    if os.path.exists(input_txt_windows):
        trace_result_summary.append("Here is the converted summary of the last 2 windows (10 seconds each) of the trace:\n")
        data = pd.read_csv(f"{OUTPUT_PATH}/trace_data_dyn/ml_feature_windows.csv")
        column_names = data.columns.tolist()

        count = 0
        for index, row in data.iterrows():
            count += 1
            if count <= len(data) - n:
                continue

            row_summary = generate_summary_row(row, column_names)
            trace_result_summary.append(f"Time window {count}:{row_summary}\n")

    trace_result = "".join(trace_result_summary)

    return trace_result

def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

def generate_trace_model(trace_result, trace_image_path):
    '''
    Function to ask gpt to generate a trace based upon the result and the 
    image showing the trace.

    Parameters:
    - trace_result (str): The trace result
    - trace_image_path (str): The path of the trace
    '''

    system_prompt = [
        "I have a highly customizable code that contains the following parameters in json format. \n",
        "start_time: The start time of the workload. ",
        "duration: The duration of the workload. ",
        "key_access_dist to specify the key access distribution - random, sequential, zipfian, two_term_exp, exponential. ",
        "zipfian_theta to specify the parameters for the zipfian key access distribution. ",
        "qps_distribution to specify the throughput distribution - uniform, sine. ",
        "sine_period, sine_amplitude, and sine_offset to specify the parameters for the sine throughput distribution. ",
        "get_ratio, put_ratio, and seek_ratio to specify the query ratio. ",
        "num_clients to specify the number of threads to simulate. ",
        "value_size_dist to specify the value size distribution - fixed, noisy, normal. ",
        "value_size_mean, value_size_stddev, and value_size_noise to specify the parameters for the normal value size distribution. ",
        "The json looks like this: \n",
        "```json\n",
        "{\
            \"benchmarks\":  [\
            {\
                \"start_time\": 0,\
                \"duration\": 0,\
                \"key_access_dist\": \"random\",\
                \"zipfian_theta\": 0,\
                \"qps_distribution\": \"uniform\",\
                \"sine_period\": 0,\
                \"sine_amplitude\": 0,\
                \"sine_offset\": 0,\
                \"get_ratio\": 0,\
                \"put_ratio\": 0,\
                \"seek_ratio\": 0,\
                \"num_clients\": 1,\
                \"value_size_dist\": \"fixed\",\
                \"value_size_mean\": 0,\
                \"value_size_stddev\": 0,\
                \"value_size_noise\": 0\
            },\
        ]}\n",
        "```\n",
        "I need to generate a trace that replicates the workload characteristics of the trace I have attached.",
    ]

    prompt_text = [
        "I have a trace from a single-threaded RocksDB workload and need to replicate it. ",
        "Different operations may be interleaved and performed in any order. The following are the results from a query level trace: ",
        f"\n{trace_result}\n",
        "Please provide me with the necessary json file (enclose it within a single ```json) ",
        "that can be run directly without changes to run a benchmark based on this trace."
    ]

    # base64_image = encode_image(trace_image_path)
    system_content = [
        {
            "type": "text",
            "text": "".join(system_prompt),
        },
    ]
    user_content = [
        {
            "type": "text",
            "text": "".join(prompt_text),
        },
        # {
        #     "type": "image_url",
        #     "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
        # },
    ]

    # Send request to GPT
    response = send_gpt_request(system_content, user_content, 0.5)
    return response

def save_model_as_json(model_response):

    # Use regex to find the JSON block within the triple backticks
    match = re.search(r'```json(.*?)```', model_response, re.DOTALL)
    if match:
        json_str = match.group(1).strip()
        try:
            json_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return None
    else:
        print("No JSON block found")
        return None

    if json_data:
        with open(f"{OUTPUT_PATH}/trace_model.json", "w") as json_file:
            json.dump(json_data, json_file, indent=4)
    else: 
        print("Something really went wrong")

    return json_data
