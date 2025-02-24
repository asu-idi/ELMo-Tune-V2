from abstraction.abstraction import convert_options_to_randomdb
from gpt.content_generator import *
from utils.constants import ABSTRACTION

def generate_option_file_with_gpt(case, previous_option_files, db_bench_args, device_information, trace_result, temperature=0.4, average_cpu_used=-1.0, average_mem_used=-1.0, test_name="fillrandom", version="8.8.1"):
    """
    Function that generates an options file for RocksDB based on specified parameters and case scenarios.
    - This function selects one of three different approaches to generate a RocksDB configuration options file. 
    
    Parameters:
    - case (int): Determines the approach to use for generating the options file. Valid values are 1, 2, or 3.
    - previous_option_files (list): A list of tuples containing past options file configurations and other relevant data.
    - device_information (str): Information about the device/system on which RocksDB is running.
    - trace_result (str): Information about tracefile summary.
    - temperature (float, optional): Controls the randomness/creativity of the generated output. Default is 0.4.
    - average_cpu_used (float, optional): Average CPU usage, used for tuning the configuration. Default is -1.0, indicating not specified.
    - average_mem_used (float, optional): Average memory usage, used for tuning the configuration. Default is -1.0, indicating not specified.
    - test_name (str, optional): Identifier for the type of test or configuration scenario. Default is "fillrandom".

    Returns:
    - tuple: A tuple containing the generated options file, reasoning behind the options, and an empty string as a placeholder.

    Raises:
    - ValueError: If the `case` parameter is not 1, 2, or 3.
    """
    def case_1(previous_option_files, db_bench_args, device_information, trace_result, temperature,average_cpu_used, average_mem_used, test_name):
        log_update("[OG] Generating options file with long option changes")
        print("[OG] Generating options file with long option changes")
        system_content = generate_system_content(device_information, trace_result)
        previous_option_file, _, _, _ = previous_option_files[-1]
        user_contents = generate_default_user_content(previous_option_file, previous_option_files, average_cpu_used, average_mem_used, test_name)
        user_contents += user_content_for_db_bench_args(db_bench_args)
        matches = request_gpt(system_content, user_contents, None, temperature)
        # Process the GPT-generated response 

        clean_options_file = ""
        reasoning = ""
        changed_value_dict = {}

        if matches is not None:
            clean_options_file, changed_value_dict, db_bench_args = cleanup_options_file(matches.group(2), db_bench_args)
            reasoning = matches.group(1) + matches.group(3)

        return clean_options_file, db_bench_args, reasoning, changed_value_dict

    def case_2(previous_option_files, db_bench_args, device_information, trace_result, temperature,average_cpu_used, average_mem_used, test_name):
        log_update("[OG] Generating options file with short option changes")
        print("[OG] Generating options file with short option changes")
        system_content = generate_system_content(device_information, trace_result)
        previous_option_file, _, _, _ = previous_option_files[-1]

        # Define a regular expression pattern to match key-value pairs
        pattern = re.compile(r'\s*([^=\s]+)\s*=\s*([^=\s]+)\s*')

        # Extract key-value pairs from the string
        key_value_pairs = {match.group(1): match.group(
            2) for match in pattern.finditer(previous_option_file)}

        # Remove key-value pairs where the key is "xxx" (case-insensitive)
        key_value_pairs = {key: value for key, value in key_value_pairs.items(
        ) if key.lower() not in {'rocksdb_version', 'options_file_version'}}

        # Split key-value pairs into chunks of 5 pairs each
        pairs_per_chunk = 20
        chunks = [list(key_value_pairs.items())[i:i + pairs_per_chunk]
                for i in range(0, len(key_value_pairs), pairs_per_chunk)]

        # Create strings for each chunk
        chunk_strings = [
            '\n'.join([f"{key}: {value}" for key, value in chunk]) for chunk in chunks]

        clean_options_file = ""
        reasoning = ""
        changed_value_dict = {}

        # Loop through each part and make API calls
        for index, chunk_string in enumerate(chunk_strings):
            user_contents = generate_default_user_content(chunk_string, previous_option_files, average_cpu_used, average_mem_used, test_name)
            if index == 0:
                user_contents += user_content_for_db_bench_args(db_bench_args)
            matches = request_gpt(system_content, user_contents, None, temperature)
            if matches is not None:
                clean_options_file, changed_value_dict_part, db_bench_args = cleanup_options_file(matches.group(2), db_bench_args)
                reasoning += matches.group(1) + matches.group(3)
                changed_value_dict.update(changed_value_dict_part)

        return clean_options_file, db_bench_args, reasoning, changed_value_dict


    def case_3(previous_option_files, db_bench_args, device_information, trace_result, temperature,average_cpu_used, average_mem_used, test_name):
        
        log_update("[OG] Generating options file with differences")
        print("[OG] Generating options file with differences")
        system_content = generate_system_content(device_information, trace_result)
        # Request GPT to generate new option
        user_contents = generate_user_content_with_difference(previous_option_files, average_cpu_used, average_mem_used, test_name)
        user_contents += user_content_for_db_bench_args(db_bench_args)
        matches = request_gpt(system_content, user_contents, None, temperature)

        clean_options_file = ""
        reasoning = ""
        changed_value_dict = {}

        # Process the GPT response
        if matches is not None:
            clean_options_file, changed_value_dict, db_bench_args = cleanup_options_file(matches.group(2), db_bench_args)
            reasoning = matches.group(1) + matches.group(3)

        return clean_options_file, db_bench_args, reasoning, changed_value_dict

    def case_4(previous_option_files, db_bench_args, device_information, trace_result, temperature, average_cpu_used, average_mem_used, test_name):
        log_update("[OG] Generating options file with resource usage info")
        print("[OG] Generating options file with resource usage info")
        system_content = generate_system_content(device_information, version)
        user_contents = generate_resource_usage_content(previous_option_files, average_cpu_used, average_mem_used, test_name)
        
        clean_options_file = ""
        reasoning = ""
        changed_value_dict = {}

        # Loop through each part and make API calls
        for index, chunk_string in enumerate(user_contents):
            user_content = generate_default_user_content(chunk_string, previous_option_files, average_cpu_used, average_mem_used, test_name)
            if index == 0:
                user_content += user_content_for_db_bench_args(db_bench_args)
            matches = request_gpt(system_content, user_content, None, temperature)
            if matches is not None:
                clean_options_file, changed_value_dict_part, db_bench_args = cleanup_options_file(matches.group(2), db_bench_args)
                reasoning += matches.group(1) + matches.group(3)
                changed_value_dict.update(changed_value_dict_part)
        
        return clean_options_file, db_bench_args, reasoning, changed_value_dict

    if ABSTRACTION:
        previous_option_files = convert_options_to_randomdb(previous_option_files)
    
    switch = {
        1: case_1,
        2: case_2,
        3: case_3,
        4: case_4,
    }
    func = switch.get(case)
    if func:
        return func(previous_option_files, db_bench_args, device_information, trace_result, temperature,average_cpu_used, average_mem_used, test_name)
    else:
        raise ValueError(f"No function defined for case {case}")
        