import re
from difflib import Differ
from options_files.ops_options_file import cleanup_options_file, parse_db_bench_args_to_dict
from gpt.gpt_request import request_gpt
from utils.filter import DB_BENCH_ARGS
from utils.utils import log_update
from dotenv import load_dotenv
import configparser
from utils.constants import ABSTRACTION, VERSION
from utils.constants import RAG, CASE_NUMBER

load_dotenv()

def generate_system_content(device_information, trace_result):
    """
    Function to generate the system content with device info and rocksDB version.
    
    Parameters:
        device_information (str): Information about the device.
        
    Returns:
        str: A prompt for configuring RocksDB for enhanced performance.
    """

    if ABSTRACTION:
        content = (
            "You are a really familiar with Log Structured Merge Tree based Key "
            "Value Store databases. We found some new database called LuminaStore and "
            "it is an LSM based KVS. You are being consulted help improve LuminaStore performance. "
            "Try to explain the reasoning behind the changed option, and only change 10 options. "
            f"The Device information is: {device_information}. "
            f"The workload summary of the tracefile is: {trace_result}"
        )
    else:
        content = (
            "You are a RocksDB Expert. "
            "You are being consulted by a company to help improve their RocksDB configuration "
            "by optimizing their options file based on their System information and benchmark output. "
            f"Only provide options files for rocksdb version {VERSION}. Also, Direct IO will always be used for both flush and compaction. "
            "Additionally, compression type is set to none always."
            "First Explain the reasoning, only change 10 options, then show the option file in original format."
            f"The Device information is: {device_information}. "
            f"The workload summary of the tracefile is: {trace_result}"
        )
    return content

def generate_benchmark_info(test_name, benchmark_result, average_cpu_used, average_mem_used):
    """
    Function to create a formatted string with benchmark information.

    Parameters:
    - test_name: Name of the test.
    - benchmark_result: Dictionary with benchmark results.
    - average_cpu_used: Average CPU usage.
    - average_mem_used: Average Memory usage.

    Returns:
    - A formatted string with all benchmark information.
    """
    benchmark_line = (f"Write/Read speed: {benchmark_result['data_speed']} "
                      f"{benchmark_result['data_speed_unit']}, Operations per second: {benchmark_result['ops_per_sec']}.")
    
    if average_cpu_used != -1 and average_mem_used != -1:
        benchmark_line += f" CPU used: {average_cpu_used}%, Memory used: {average_mem_used}% during test."
    
    return benchmark_line

def user_content_for_db_bench_args(db_bench_args):
    args_dict = {key: "-1" for key in DB_BENCH_ARGS}
    args_dict.update(parse_db_bench_args_to_dict(db_bench_args))
    args = "\n".join(f"--{key}={value}" for key, value in args_dict.items())
    return [(
        "If and only if demanded by the workload, you can also update these arguments:\n"
        f"```\n[DBBenchOptions]\n{args}\n```"
        "to improve the performance of the database. "
        "Put it at the first line of the options file if you want to update it."
    )]

def generate_default_user_content(chunk_string, previous_option_files, average_cpu_used=-1.0, average_mem_used=-1.0, test_name="fillrandom"):
    user_contents = []
    for _, benchmark_result, reasoning, _ in previous_option_files[1: -1]:
        benchmark_line = generate_benchmark_info(test_name, benchmark_result, average_cpu_used, average_mem_used)
        user_content = f"The option file changes were:\n```\n{reasoning}\n```\nThe benchmark results are: {benchmark_line}"
        user_contents.append(user_content)

    _, benchmark_result, _, _ = previous_option_files[-1]
    benchmark_line = generate_benchmark_info(test_name, benchmark_result, average_cpu_used, average_mem_used)
    if CASE_NUMBER == 2:
        user_content = f"Part of the current option file is:\n```\n{chunk_string}\n```\nThe benchmark results are: {benchmark_line}"
        user_contents.append(user_content)
        user_contents.append("Based on these information generate a new file only with the options provided above (but only give the changed value) to improve my database performance. Enclose the new options file in ```.")
    else:
        user_content = f"Part of the current option file is:\n```\n{chunk_string}\n```\nThe benchmark results are: {benchmark_line}"
        user_contents.append(user_content)
        user_contents.append("Based on these information generate a new file in the same format as the options_file (but only give the changed value) to improve my database performance. Enclose the new options file in ```.")
    return user_contents

def generate_assistant_content(previous_option_files):
    assistant_contents = []

    for _, _, reasoning, changes_dict in previous_option_files[1:]:
        changes_str = "\n".join(f"{k}={v}" for k, v in changes_dict.items())
        assistant_contents.append((
            f"{reasoning}\n"
            "The options changes were:\n"
            f"```\n{changes_str}\n```"
        ))

    return assistant_contents

def generate_user_content_with_difference(previous_option_files, average_cpu_used=-1.0, average_mem_used=-1.0, test_name="fillrandom"):
    result = ""
    user_content = []

    if len(previous_option_files) == 1:
        m1_file, m1_benchmark_result, _, _ = previous_option_files[-1]
        benchmark_line = generate_benchmark_info(test_name, m1_benchmark_result, average_cpu_used, average_mem_used)
        user_content = f"The original file is:\n```\n{m1_file}\n```\nThe benchmark results for the original file are: {benchmark_line}"
    
    elif len(previous_option_files) > 1:
        previous_option_file1, _, _, _ = previous_option_files[-1]
        previous_option_file2, _, _, _ = previous_option_files[-2]

        pattern = re.compile(r'\s*([^=\s]+)\s*=\s*([^=\s]+)\s*')

        file1_lines = pattern.findall(previous_option_file1)
        file2_lines = pattern.findall(previous_option_file2)

        file1_lines = ["{} = {}".format(k, v) for k, v in file1_lines]
        file2_lines = ["{} = {}".format(k, v) for k, v in file2_lines]
        differ = Differ()
        diff = list(differ.compare(file1_lines, file2_lines))
        lst= []
        for line in diff:
            if line.startswith('+'):
                lst.append(line)
        result = '\n'.join(line[2:] for line in lst)
        m1_file, m1_benchmark_result, _, _ = previous_option_files[-1]
        benchmark_line = generate_benchmark_info(test_name, m1_benchmark_result, average_cpu_used, average_mem_used)
        user_content = (
            f"The original file is:\n```\n{m1_file}\n```\n"
            f"The benchmark results for the original file are: {benchmark_line}\n"
            f"The previous file modifications are:\n```\n{result}\n```\n"
        )
    
    else:
        _, benchmark_result, _, _ = previous_option_files[-1]
        benchmark_line = generate_benchmark_info(test_name, benchmark_result, average_cpu_used, average_mem_used)

        user_content = ("The previous file modifications are: "
                         f"\n```\n{result}\n```\n"
                         f"The benchmark results for the previous file are: {benchmark_line}")
    
    
    user_contents = [user_content, "Based on these information generate a new file in the same format as the options_file (but only give the changed value) to improve my database performance. Enclose the new options file in ```."]
    return user_contents

def midway_options_file_generation(options, db_bench_args, avg_cpu_used, avg_mem_used, last_throughput, device_information, trace_result, options_file):
    """
    Function to generate a prompt for the midway options file generation.
    
    Returns:
    - str: A prompt for the midway options file generation.
    """

    system_content = generate_system_content(device_information, trace_result)

    user_content = []
    content = "Can you generate a new options file for RocksDB based on the following information?\n"
    content += "The previous options file is:\n"

    content += "```\n"
    content += options_file[-1][0]
    content += "```\n"

    content += (
        f"The throughput results for the above options file are: {options_file[-1][1]['ops_per_sec']}. "
    )

    user_content.append(content)
    content = ""

    content += "We then made the following changes to the options file:\n"

    pattern = re.compile(r'\s*([^=\s]+)\s*=\s*([^=\s]+)\s*')

    file1_lines = pattern.findall(options)
    file2_lines = pattern.findall(options_file[-1][0])

    file1_lines = ["{} = {}".format(k, v) for k, v in file1_lines]
    file2_lines = ["{} = {}".format(k, v) for k, v in file2_lines]
    differ = Differ()
    diff = list(differ.compare(file1_lines, file2_lines))
    lst= []
    for line in diff:
        if line.startswith('+'):
            lst.append(line)
    result = '\n'.join(line[2:] for line in lst)

    content += "```\n"
    content += result
    content += "```\n"

    content += f"\nThe updated file has a throughput of: {last_throughput}. \n\n"
    # CPU and Memory Information
    content += "The current CPU and Memory usage for the workload was: "
    content += f"{avg_cpu_used}% and {avg_mem_used}\n"
    
    user_content.append(content)
    content = ""
    content += "Based on this information generate a new file (but only give the changed value). Enclose the new options in ```. Feel free to use upto 100% of the CPU and Memory."
    user_content.append(content)

    log_update("[OG] Generating options file with differences")
    log_update("[OG] Prompt for midway options file generation")
    log_update(content)
    matches = request_gpt(system_content, user_content, None, 0.4)

    clean_options_file = ""
    reasoning = ""
    changed_value_dict = {}

    if matches is not None:
        clean_options_file, changed_value_dict, db_bench_args = cleanup_options_file(matches.group(2), db_bench_args)
        reasoning = matches.group(1) + matches.group(3)

    return clean_options_file, db_bench_args, reasoning, changed_value_dict


def dynamic_options_file_generation(prev_options, db_bench_args, avg_cpu_used, avg_mem_used, last_throughput, device_information, trace_result, options_file):
    """
    Function to generate a prompt for the dynamic options file generation.

    Returns:
    - str: A prompt for the dynamic options file generation.
    """

    sys_content = (
        "You are a RocksDB Expert being consulted by a company to help improve their RocksDB performance "
        "by optimizing the mutable options while the workloads is running."
        f"Direct IO will always be used. Additionally, compression type is set to none always. "
        "Respond with the the reasoning first, then show the options in original format."
        f"The Device information is: {device_information}"
    )

    db_options = [
        'max_background_jobs',
        'max_background_compactions',
        'max_subcompactions',
        'avoid_flush_during_shutdown',
        'writable_file_max_buffer_size',
        'delayed_write_rate',
        'max_total_wal_size',
        'delete_obsolete_files_period_micros',
        'stats_dump_period_sec',
        'stats_persist_period_sec',
        'stats_history_buffer_size',
        'max_open_files',
        'bytes_per_sync',
        'wal_bytes_per_sync',
        'strict_bytes_per_sync',
        'compaction_readahead_size',
        'max_background_flushes'
    ]

    user_content = []

    # Previous User content
    for opt_file in options_file[-3:-1]:
        values = {}
        opt_string = ""
        for line in opt_file[0].split('\n'):
            for var in db_options:
                pattern = rf'\b{var}\b\s*=\s*(\S+)'
                match = re.search(pattern, line)
                if match:
                    values[var] = match.group(1)
        
        for var, val in values.items():
            opt_string += f"{var} = {val}\n"

        content = "The previous options file is:\n"
        content += "```\n"
        content += opt_string
        content += "```\n"
        content += (
            f"The throughput results for the above options file are: {opt_file[1]['ops_per_sec']}. "
        )
        user_content.append(content)

    # Last User content (question)
    content = "Can you generate a new options for RocksDB based on the following information?\n"
    
    # Trace Information
    content += f"The trace from the last 20 seconds of the workload is as follows:\n"
    content += f"{trace_result}\n"

    # CPU and Memory Information
    content += "The CPU and Memory usage during the last 20 seconds of the workload was: "
    content += f"{avg_cpu_used}% and {avg_mem_used}\n"

    # Previous Options Information
    content += "The previous db_options values for each of the MutableDBOptions are as follows:\n"

    values = {}
    for line in options_file[-1][0].split('\n'):
        for var in db_options:
            pattern = rf'\b{var}\b\s*=\s*(\S+)'
            match = re.search(pattern, line)
            if match:
                values[var] = match.group(1)
    
    for var, val in values.items():
        content += f"{var} = {val}\n"

    content += (
        f"The throughput results for the above options file are: {options_file[-1][1]['ops_per_sec']}. "
    )
    if (len(options_file) > 1):
        if (options_file[-1][1]['ops_per_sec'] > options_file[-2][1]['ops_per_sec']):
            content += (
                "Which is an improvement from the previous throughput of "
                f"{options_file[-2][1]['ops_per_sec']}. "
                "Keep it up!. "
                "Based on this information generate a new file. "
            )
        else:
            content += (
                "Which is a decrease from the previous throughput of "
                f"{options_file[-2][1]['ops_per_sec']}. "
                "Please revert the changes made in the previous file, "
                "and generate a new file but different approach from the previous one. "
            )
            
    content += "Enclose the new options in ```. Feel free to use upto 100% of the CPU and Memory."
    user_content.append(content)

    log_update("[OG] Generating options file with differences")
    log_update("[OG] Prompt for Dynamic options file generation")
    matches = request_gpt(sys_content, user_content, None, 0.4)

    clean_options_file = ""
    reasoning = ""
    changed_value_dict = {}

    if matches is not None:
        clean_options_file, changed_value_dict, db_bench_args = cleanup_options_file(matches.group(2), db_bench_args)
        reasoning = matches.group(1) + matches.group(3)
    return clean_options_file, db_bench_args, reasoning, changed_value_dict

def error_correction_options_file_generation(error_options, db_bench_args, reasoning, changed_value_dict, error_reason, iteration):
    """
    Function to generate a prompt for the error correction options file generation.

    Returns:
    - str: A prompt for the error correction options file generation.
    """    
    system_content = (
        "You are a RocksDB Expert being consulted by a company to help improve their RocksDB performance "
        "by optimizing the options configured for a particular scenario they face."
        "But there was an error in the options file generated. "
        "Respond with the error reasoning first, then show the corrected option file in original format."
        f"Only provide options files for rocksdb version {VERSION}. "
        "Enclose the new options in ```"
    )

    args_dict = parse_db_bench_args_to_dict(db_bench_args)
    args = "\n".join(f"{key}={value}" for key, value in args_dict.items())

    user_content = [(
        "The options file generated had an error. This is the options file that was generated:\n"
        "```\n"
        f"{args}\n"
        f"{error_options}"
        "```\n"
        "The error in the options file was:\n"
        f"{error_reason}"
        "Fix the error and generate a new file (but only give the changed value). Enclose the new options in ```."
    )]

    print("[OG] Generating options file to correct error")
    log_update("[OG] Generating options file to correct error")
    matches = request_gpt(system_content, user_content, None, 0.4)

    clean_options_file = ""
    
    if matches is not None:
        clean_options_file, changed_value_dict_part, db_bench_args = cleanup_options_file(matches.group(2), db_bench_args)
        reasoning += "\n"+ matches.group(1) + matches.group(3)
    
    changed_value_dict.update(changed_value_dict_part)
    return clean_options_file, db_bench_args, reasoning, changed_value_dict

def generate_resource_usage_content(previous_option_files, average_cpu_used=-1.0, average_mem_used=-1.0, test_name="fillrandom"):
    """
    Function to generate a prompt on resource usage parameters.

    Returns:
        str: A formatted string containing the categorized resource usage parameters. 

    """
    result =" "
    user_content = []

    previous_option_file1, _, _, _ = previous_option_files[-1]
    config = configparser.ConfigParser()
    config.read_string(previous_option_file1)

    resource_usage = {
        'CPU': [
            'max_background_flushes', 'max_background_compactions', 'max_background_jobs', 
            'max_file_opening_threads', 'max_subcompactions', 'enable_thread_tracking',
            'write_thread_max_yield_usec', 'write_thread_slow_yield_usec', 'enable_write_thread_adaptive_yield',
            'two_write_queues', 'compaction_style', 'compaction_pri', 'level0_file_num_compaction_trigger',
            'level0_slowdown_writes_trigger', 'level0_stop_writes_trigger', 'paranoid_checks', 
            'verify_sst_unique_id_in_manifest', 'use_adaptive_mutex'
        ],
        'Storage': [
            'max_open_files', 'compaction_readahead_size', 'wal_bytes_per_sync', 'bytes_per_sync',
            'delete_obsolete_files_period_micros', 'max_total_wal_size', 'strict_bytes_per_sync',
            'writable_file_max_buffer_size', 'log_file_time_to_roll', 'max_log_file_size',
            'manifest_preallocation_size', 'allow_data_in_errors', 'WAL_ttl_seconds', 'recycle_log_file_num',
            'file_checksum_gen_factory', 'keep_log_file_num', 'random_access_max_buffer_size', 
            'access_hint_on_compaction_start', 'manual_wal_flush', 'use_direct_reads', 
            'use_direct_io_for_flush_and_compaction', 'allow_mmap_writes', 'allow_mmap_reads', 
            'advise_random_on_open', 'db_write_buffer_size'
        ],
        'Advanced': [
            'stats_history_buffer_size', 'stats_dump_period_sec', 'stats_persist_period_sec', 
            'info_log_level', 'enable_pipelined_write', 'persist_stats_to_disk', 'WAL_size_limit_MB', 
            'fail_if_options_file_error', 'db_host_id', 'wal_recovery_mode', 'wal_filter', 'allow_2pc', 
            'unordered_write', 'track_and_verify_wals_in_manifest', 'skip_checking_sst_file_sizes_on_db_open', 
            'skip_stats_update_on_db_open', 'force_consistency_checks', 'memtable_whole_key_filtering', 
            'cache_index_and_filter_blocks', 'cache_index_and_filter_blocks_with_high_priority', 
            'pin_l0_filter_and_index_blocks_in_cache', 'allow_ingest_behind', 'avoid_unnecessary_blocking_io', 
            'write_dbid_to_manifest', 'best_efforts_recovery', 'enable_write_thread_adaptive_yield', 
            'flush_verify_memtable_count', 'create_missing_column_families', 'create_if_missing', 
            'is_fd_close_on_exec', 'enforce_single_del_contracts'
        ],
        'Memory': [
            'write_buffer_size', 'max_write_buffer_number', 'arena_block_size', 'max_bytes_for_level_base',
            'max_bytes_for_level_multiplier', 'target_file_size_base', 'max_compaction_bytes', 'block_size',
            'block_restart_interval', 'pin_top_level_index_and_filter', 'max_write_batch_group_size_bytes',
            'write_thread_max_yield_usec', 'db_write_buffer_size'
        ]
    }
    categorized_parameters = {category: {} for category in resource_usage}
    for section in config.sections():
        for key, value in config.items(section):
            for category, params in resource_usage.items():
                if key in params:
                    categorized_parameters[category][key] = value

    result = {category: [] for category in resource_usage}
    for category in ['CPU', 'Storage', 'Advanced', 'Memory']:
        result[category].append(f"{category} Parameters:\n")
        for param, value in categorized_parameters[category].items():
            result[category].append(f"  {param}= {value}\n")
        result[category].append("\n")

    # Format each category into a code block
    for category in ['CPU', 'Storage', 'Advanced', 'Memory']:
        user_content.append(f"```\n{''.join(result[category])}```\n")
    return user_content