import utils.constants as constants
from utils.graph import plot, plot_multiple
from utils.system_operations.fio_runner import get_fio_result
from options_files.ops_options_file import parse_option_file_to_dict, get_initial_options_file

import rocksdb.subprocess_manager as spm
from utils.utils import log_update, store_best_option_file, path_of_db, store_diff_options_list
from utils.system_operations.get_sys_info import system_info
from gpt.prompts_generator import generate_option_file_with_gpt
from trace_analyzer.analyzer import analyze_tracefile, generate_trace_model, save_model_as_json
import os

def main():
    '''
    Main function to run the project. This function will run the db_bench with the initial options file and then
    generate new options files using GPT API and run db_bench with the new options file. This function will also
    store the output of db_bench in a file. The output file will contain the benchmark results, the options file
    used to generate the benchmark results and the reasoning behind the options file as provided by the GPT API.
    There will be a separate file for each iteration.

    Parameters:
    - None

    Returns:
    - None
    '''

    # initialize variables
    options_files = []
    options_list = []

    # Set up the path
    output_folder_dir = constants.OUTPUT_PATH
    os.makedirs(output_folder_dir, exist_ok=True)
    db_path = path_of_db()
    fio_result = get_fio_result(constants.FIO_RESULT_PATH)

    log_update(f"[MFN] Starting the program with the case number: {constants.CASE_NUMBER}")
    print(f"[MFN] Starting the program with the case number: {constants.CASE_NUMBER}")

    # Check if the tracefile is not None
    if constants.TRACEFILE_PATH:
        print("[MFN] Tracefile provided. Running trace analyzer.")
        log_update("[MFN] Tracefile provided. Running trace analyzer.")

        trace_result = analyze_tracefile(constants.TRACEFILE_PATH)
        model_response = generate_trace_model(trace_result, "")
        json_model = save_model_as_json(model_response)

        if constants.PRE_LOAD_CMD != "":
            print("[MFN] Pre-load command not provided. Command necessary for TRACEFILE based runs.\n"
                  "Run with empty string if tracefile does not need preload. Exiting.")
            log_update("[MFN] Pre-load command not provided. Command necessary for TRACEFILE based runs."
                       "Run with empty string if tracefile does not need preload. Exiting.")
            exit(1)

        if constants.TEST_NAME != "tracefile":
            print("[MFN] Test name is not tracefile. You might want to check that.")
            log_update("[MFN] Test name is not tracefile. You might want to check that.")

    # First run, Initial options file and see how the results are
    options, reasoning = get_initial_options_file()

    is_error, benchmark_results, average_cpu_usage, average_memory_usage, options = spm.benchmark(
        db_path, options, output_folder_dir, reasoning, None, 0, None, options_files, [])

    if is_error:
        # If the initial options file fails, exit the program
        log_update("[MFN] Failed to benchmark with the initial options file. Exiting.")
        print("[MFN] Failed to benchmark with the initial options file. Exiting.")
        exit(1)
    else:
        # Run trace_analyzer
        trace_result = analyze_tracefile(db_path + "/tracefile")

        # If the initial options file succeeds, store the options file and benchmark results, pass it to the GPT API to generate a new options file
        parsed_options = parse_option_file_to_dict(options)
        options_list.append(parsed_options)

        # Maintain a list of options files, benchmark results and why that option file was generated
        options_files.append((options, benchmark_results, reasoning, ""))
        db_bench_args = []

        iteration_count = constants.ITERATION_COUNT

        for i in range(1, iteration_count + 1):

            log_update(f"[MFN] Starting iteration {i}")
            log_update(f"[MFN] Querying ChatGPT for next options file")

            print("-" * 50)
            print(f"[MFN] Starting iteration {i}")

            print("[MFN] Querying ChatGPT for next options file")
            temperature = 0.4
            retry_counter = 5
            generated = False

            for gpt_query_count in range(retry_counter, 0, -1):
                # Generate new options file with retry limit of 5

                new_options_file, db_bench_args, reasoning, changed_value_dict = generate_option_file_with_gpt(
                    constants.CASE_NUMBER, options_files, db_bench_args,
                    system_info(db_path, fio_result), trace_result, temperature,
                    average_cpu_usage, average_memory_usage, 
                    constants.TEST_NAME)
                if new_options_file is None:
                    log_update(f"[MFN] Failed to generate options file. Retrying. Retries left: {gpt_query_count - 1}")
                    print("[MFN] Failed to generate options file. Retrying. Retries left: ", gpt_query_count - 1)
                    continue

                # Parse output
                is_error, benchmark_results, average_cpu_usage, average_memory_usage, new_options_file = spm.benchmark(
                    db_path, new_options_file, output_folder_dir, reasoning, changed_value_dict, iteration_count, benchmark_results, options_files, db_bench_args)
                if is_error:
                    log_update(f"[MFN] Benchmark failed. Retrying with new options file. Retries left: {gpt_query_count - 1}")
                    print("[MFN] Benchmark failed. Retrying with new options file. Retries left: ", gpt_query_count - 1)
                    temperature += 0.1
                    continue
                else:
                    generated = True
                    break

            if generated:
                options = new_options_file
                options_files.append((options, benchmark_results, reasoning,
                                      changed_value_dict))
                parsed_options = parse_option_file_to_dict(options)
                options_list.append(parsed_options)

                # Graph Ops/Sec
                plot([e[1]["ops_per_sec"] for e in options_files], f"OpsPerSec {constants.TEST_NAME}",
                     f"{output_folder_dir}/OpsPerSec.png")
                plot_multiple(options_files, "Ops Per Second",
                              f"{output_folder_dir}/opsM_per_sec.png")
        
            else:
                log_update("[MFN] Failed to generate options file over 5 times. Exiting.")
                print("[MFN] Failed to generate options file over 5 times. Exiting.")
                exit(1)
            
            store_diff_options_list(options_list, output_folder_dir)

        store_best_option_file(options_files, output_folder_dir)

        # Graph Ops/Sec
        plot([e[1]["ops_per_sec"] for e in options_files], f"OpsPerSec {constants.TEST_NAME}",
             f"{output_folder_dir}/OpsPerSec.png")
        plot_multiple(options_files, "Ops Per Second",
                      f"{output_folder_dir}/opsM_per_sec.png")
        
        store_diff_options_list(options_list, output_folder_dir)


if __name__ == "__main__":
    main()
