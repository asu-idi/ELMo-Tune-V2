import subprocess
import os
import time
from cgroup_monitor import CGroupMonitor, CGroupManager

from gpt.content_generator import error_correction_options_file_generation
from utils.utils import log_update, path_of_db
from utils.constants import ERROR_CORRECTION_COUNT, FINETUNE_ITERATION, TEST_NAME, DB_BENCH_PATH, OPTIONS_FILE_DIR, NUM_ENTRIES, DURATION, SIDE_CHECKER, FIO_RESULT_PATH, DYNAMIC_OPTION_TUNING
from utils.constants import SINE_WRITE_RATE_INTERVAL_MILLISECONDS, SINE_A, SINE_B, SINE_C, SINE_D, OUTPUT_PATH, PRE_LOAD_CMD, NUM_THREADS, PRE_LOAD_DB_PATH
from rocksdb.parse_db_bench_output import parse_db_bench_output
from rocksdb.fine_tune import fine_tuning
from utils.utils import store_db_bench_output
from utils.graph import plot_2axis
from utils.mmap_utils import add_mmap_file_to_option, create_mmap_file, write_to_mmap_file
from gpt.prompts_generator import midway_options_file_generation, dynamic_options_file_generation
from utils.system_operations.fio_runner import get_fio_result
from utils.system_operations.get_sys_info import system_info
from trace_analyzer.analyzer import analyze_tracefile, analyze_last_n_tracefile_windows


def pre_tasks(database_path, run_count):
    '''
    Function to perform the pre-tasks before running the db_bench
    Parameters:
    - database_path (str): The path to the database
    - run_count (str): The current iteration of the benchmark

    Returns:
    - None
    '''

    # Try to delete the database if path exists 
    proc = subprocess.run(
        f'rm -rf {database_path}',
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True,
        check=False
    )

    log_update("[SPM] Flushing the cache")
    print("[SPM] Flushing the cache")
    # Delay for all the current memory to be freed
    proc = subprocess.run(
        f'sync; echo 3 > /proc/sys/vm/drop_caches',
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True,
        check=False
    )

    # update_log_file("[SPM] Waiting for 90 seconds to free up memory, IO and other resources")
    print("[SPM] Waiting for 30 seconds to free up memory, IO and other resources")
    # Give a 1.5 min delay for all the current memory/IO/etc to be freed
    time.sleep(30)


def generate_db_bench_command(db_bench_path, database_path, options, run_count, test_name, db_bench_extra_args=[]):
    '''
    Generate the DB bench command

    Parameters:
    - db_bench_path (str): The path to the db_bench executable
    - database_path (str): The path to the database
    - option_file (dict): The options file to be used
    - run_count (str): The current iteration of the benchmark
    - test_name (str): The name of the test
    - db_bench_extra_args (list): Extra arguments to be passed to db_bench

    Returns:
    - list: The db_bench command
    '''

    db_bench_command = [
        db_bench_path,
        f"--db={database_path}",
        f"--options_file={OPTIONS_FILE_DIR}",
        "--use_direct_io_for_flush_and_compaction",
        "--use_direct_reads", "--compression_type=none",
        "--stats_interval_seconds=1", "--histogram", 
        f"--dynamic_options_file=/tmp/mmap_file.mmap" if DYNAMIC_OPTION_TUNING else "",
        f"--threads={NUM_THREADS}", f"--trace_file={database_path}/tracefile",
        f"--num={NUM_ENTRIES}", f"--duration={DURATION}"
    ]

    # Preload phase - Only needed for some tests - Theoritically, mentioning test name should not be needed
    # However, I trust I will forget this in the future and this will act as a secondary measure
    if test_name == "readrandom" or test_name == "mixgraph" or test_name == "tracefile":
        if PRE_LOAD_DB_PATH != "":
            log_update("[SPM] Running Pre-load command")
            print("[SPM] Running Pre-load command")
            tmp_runner_rm = ["rm", "-rf", database_path]
            tmp_proc_rm = subprocess.run(tmp_runner_rm, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
            tmp_runner = ["cp", "-r", PRE_LOAD_DB_PATH, database_path]
            tmp_proc = subprocess.run(tmp_runner, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)

    if test_name == "fillrandom":
        db_bench_command.append("--benchmarks=fillrandom")
    elif test_name == "readrandomwriterandom":
        db_bench_command.append("--benchmarks=readrandomwriterandom")
    elif test_name == "readrandom":
        if PRE_LOAD_DB_PATH == "":
            log_update("[SPM] Running fillrandom to load the database")
            print("[SPM] Running fillrandom to load the database")
            tmp_runner = db_bench_command[:-3] + ["--num=50000000", "--benchmarks=fillrandom", "--max_background_jobs=8"]
            tmp_proc = subprocess.run(tmp_runner, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        new_db_bench = db_bench_command + ["--benchmarks=readrandom", "--use_existing_db", "--reads=5000000"]
        db_bench_command = new_db_bench
    elif test_name == "mixgraph":
        if PRE_LOAD_DB_PATH == "":
            log_update("[SPM] Running fillrandom to load the database")
            print("[SPM] Running fillrandom to load the database")
            tmp_runner = db_bench_command[:-3] + ["--num=50000000", "--benchmarks=fillrandom", "--key_size=48", "--value_size=43"]
            tmp_proc = subprocess.run(tmp_runner, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        new_db_bench = db_bench_command[:-1] + ["--benchmarks=mixgraph", "--use_existing_db", f"--duration={DURATION}", 
                                                "--mix_get_ratio=0.83", "--mix_put_ratio=0.14", "--mix_seek_ratio=0.03", "--key_size=48",
                                                f"--sine_write_rate_interval_milliseconds={SINE_WRITE_RATE_INTERVAL_MILLISECONDS}", "--sine_mix_rate", 
                                                f"--sine_a={SINE_A}", f"--sine_b={SINE_B}", f"--sine_c={SINE_C}", f"--sine_d={SINE_D}"]
        db_bench_command = new_db_bench
    elif test_name == "readwhilewriting":
        db_bench_command.append("--benchmarks=readwhilewriting")
    elif test_name == "sinetest":
        db_bench_command += [
            "--benchmarks=fillrandom", "--sine_write_rate=true",
            f"--sine_write_rate_interval_milliseconds={SINE_WRITE_RATE_INTERVAL_MILLISECONDS}",
            f"--sine_a={SINE_A}", f"--sine_b={SINE_B}", f"--sine_c={SINE_C}", f"--sine_d={SINE_D}",
        ]
    elif test_name == "jsonconfigured":
        db_bench_command += [
            "--benchmarks=jsonconfigured", 
            f"--json_file_path={os.path.join(os.path.dirname(__file__), '../benchy.json')}"
        ]
    elif test_name == "tracefile":
        if PRE_LOAD_CMD != "" and PRE_LOAD_DB_PATH == "":
            tmp_runner = PRE_LOAD_CMD.split(" ")
            tmp_proc = subprocess.run(tmp_runner, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        db_bench_command[:-2] += [
            "--benchmarks=jsonconfigured", "--use_existing_db",
            f"--json_file_path={os.path.join(OUTPUT_PATH, 'trace_model.json')}"
        ]
    else:
        print(f"[SPM] Test name {test_name} not recognized")
        exit(1)

    db_bench_command += db_bench_extra_args

    log_update(f"[SPM] Command: {db_bench_command}")
    return db_bench_command


def db_bench(db_bench_path, database_path, options, run_count, test_name, previous_throughput, options_files, db_bench_args=[], bm_iter=0):
    '''
    Store the options in a file
    Do the benchmark

    Parameters:
    - db_bench_path (str): The path to the db_bench executable
    - database_path (str): The path to the database
    - option_file (dict): The options file to be used
    - run_count (str): The current iteration of the benchmark

    Returns:
    - None
    '''
    global proc_out
    with open(f"{OPTIONS_FILE_DIR}", "w") as f:
        f.write(options)

    # Perform pre-tasks to reset the environment
    pre_tasks(database_path, run_count)
    command = generate_db_bench_command(db_bench_path, database_path, options, run_count, test_name, db_bench_args)

    # Create dynamic option file
    if DYNAMIC_OPTION_TUNING:
        create_mmap_file()

    log_update(f"[SPM] Executing db_bench with command: {command}")
    print("[SPM] Executing db_bench")


    if SIDE_CHECKER and previous_throughput != None:
        cgm = CGroupManager("llm_cgroup", helper_script=os.path.abspath("utils/root_cgroup_helper.sh"))
        cgroup_monitor = CGroupMonitor("llm_cgroup")
        
        if DYNAMIC_OPTION_TUNING:
            saved_optionfile = options_files[-1][0]
            cur_options_file = []

        start_time = time.time()
        cgroup_monitor.start_monitor()

        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True) as proc_out:
            cgm.add_process(proc_out.pid, sudo=True)

            output = ""
            first_check_interval = 100
            first_check_flag = False

            # db.h: L1412
            # dynamic options update is a heavy process that is (weirdly) foreground. 
            # So, we need to make this an infrequent call.
            check_interval = 90

            for line in proc_out.stdout:
                output += line
                elapsed_time = time.time() - start_time

                # Read based workloads need additional time to build the cache
                # This will effectively provide a small window for the throughput to stabilize
                if first_check_flag == False:
                    if (elapsed_time <= first_check_interval):
                        continue
                    else:
                        first_check_flag = True

                if elapsed_time <= check_interval:
                    continue

                if "ops/second" in line:
                    current_avg_throughput = (float(line.split("(")[2].split(",")[1].split(")")[0]))*NUM_THREADS

                    # Active flagger monitoring throughput
                    if (current_avg_throughput < .9 * float(previous_throughput)) and (bm_iter < 3):
                        print("[SQU] Throughput decreased, resetting the benchmark")
                        log_update(f"[SQU] Throughput decreased {previous_throughput}->{current_avg_throughput}, resetting the benchmark")

                        op = cgroup_monitor.stop_monitor()
                        avg_cpu_used = op["average_cpu_usage_percent"]
                        avg_mem_used = op["average_memory_usage_percent"]

                        proc_out.kill()

                        db_path = path_of_db()
                        fio_result = get_fio_result(FIO_RESULT_PATH)
                        device_info = system_info(db_path, fio_result)
                        trace_result = analyze_tracefile(db_path + "/tracefile")

                        new_options, db_bench_args, _, _ = midway_options_file_generation(options, db_bench_args, avg_cpu_used, avg_mem_used, current_avg_throughput, device_info, trace_result, options_files)
                        output, avg_cpu_used, avg_mem_used, options = db_bench(db_bench_path, database_path, new_options, run_count, test_name, previous_throughput, options_files, db_bench_args, bm_iter+1)

                        log_update("[SPM] Finished running db_bench")
                        return output, avg_cpu_used, avg_mem_used, options

                    # Dynamic Option Tuning
                    # To Do: Additional condition to check workload shift
                    if DYNAMIC_OPTION_TUNING and current_avg_throughput < 0.6 * float(previous_throughput):
                        print("[SQU] Dynamic option tuning is enabled and now running")
                        log_update("[SQU] Dynamic option tuning is enabled and now running")

                        db_path = path_of_db()
                        fio_result = get_fio_result(FIO_RESULT_PATH)
                        device_info = system_info(db_path, fio_result)

                        # Information from the last 20 seconds
                        op = cgroup_monitor.get_last_n_stats(check_interval)
                        avg_cpu_used = op["average_cpu_usage_percent"]
                        avg_mem_used = op["average_memory_usage_percent"]

                        # Integrate current trace details into dynamic option tuning
                        trace_result = analyze_last_n_tracefile_windows(db_path + "/tracefile", check_interval//10)

                        cur_options_file.append([
                            saved_optionfile,
                            {"ops_per_sec": current_avg_throughput}
                        ])

                        new_options, _, _, _ = dynamic_options_file_generation(None, db_bench_args, avg_cpu_used, avg_mem_used, None, device_info, trace_result, cur_options_file)

                        saved_optionfile = new_options

                        write_to_mmap_file(new_options)
                else:
                    print("[SQU] No throughput found in the output")
                    log_update("[SQU] No throughput found in the output")

                start_time = time.time()

        print("[SPM] Finished running db_bench")
        print("----------------------------------------------------------------------------")

        op = cgroup_monitor.stop_monitor()
        avg_cpu_used = op["average_cpu_usage_percent"]
        avg_mem_used = op["average_memory_usage_percent"]

        if DYNAMIC_OPTION_TUNING:
            options = add_mmap_file_to_option(options, saved_optionfile)

        return output, avg_cpu_used, avg_mem_used, options
    
    else:

        cgm = CGroupManager("llm_cgroup", helper_script=os.path.abspath("utils/root_cgroup_helper.sh"))
        cgm.create_cgroup()
        cgm.set_cpu_limit(4)
        cgm.set_memory_limit(4*1024*1024*1024)
        cgm.set_memory_swap_limit(4*1024*1024*1024)

        cgroup_monitor = CGroupMonitor("llm_cgroup")
        cgroup_monitor.start_monitor()

        proc_out = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        cgm.add_process(proc_out.pid, sudo=True)
        stdout, stderr = proc_out.communicate()

        op = cgroup_monitor.stop_monitor()
        avg_cpu_used = op["average_cpu_usage_percent"]
        avg_mem_used = op["average_memory_usage_percent"]

        print("[SPM] Finished running db_bench")
        print("---------------------------------------------------------------------------")
        
        return stdout, avg_cpu_used, avg_mem_used, options


def benchmark(db_path, options, output_file_dir, reasoning, changed_value_dict, iteration_count, previous_results, options_files, db_bench_args, bm_iter=0):
    '''
    Function to run db_bench with the given options file and store the output in a file

    Parameters:
    - db_path (str): The path of database
    - options (dict): The options to be used
    - output_file_dir (str): the output directory
    - reasoning (str): The reasoning of the benchmark

    Returns:
    - is_error (bool): 
    - benchmark_results (dict):
    '''
    if previous_results is None:
        output, average_cpu_usage, average_memory_usage, options = db_bench(
            DB_BENCH_PATH, db_path, options, iteration_count, TEST_NAME, None, options_files, db_bench_args)
    else:
        if FINETUNE_ITERATION <= 0:
            output, average_cpu_usage, average_memory_usage, options = db_bench(
                DB_BENCH_PATH, db_path, options, iteration_count, TEST_NAME, previous_results['ops_per_sec'], options_files, db_bench_args)
        else:
            output, average_cpu_usage, average_memory_usage, options, changed_value_dict = fine_tuning(
                db_path, options, reasoning, changed_value_dict, previous_results['ops_per_sec'], options_files, db_bench_args)

    # log_update(f"[SPM] Output: {output}")
    benchmark_results = parse_db_bench_output(output)

    contents = os.listdir(output_file_dir)
    ini_file_count = len([f for f in contents if f.endswith(".ini")])

    # ERROR: Unable to load options file*
    if benchmark_results.get("error") is not None:
        is_error = True
        log_update(f"[SPM] Benchmark failed, the error is: {benchmark_results.get('error')}")
        print("[SPM] Benchmark failed, the error is: ",
              benchmark_results.get("error"))
        # Save incorrect options in a file
        store_db_bench_output(output_file_dir,
                              f"{ini_file_count}-incorrect_options.ini",
                              benchmark_results, options, reasoning, changed_value_dict)
        # Restore previous options_file
        with open(f"{OPTIONS_FILE_DIR}", "w") as f:
            f.write(options_files[-1][0])

        if bm_iter < ERROR_CORRECTION_COUNT:
            print(f"[SPM] Retrying the benchmark with error correction {bm_iter+1}/{ERROR_CORRECTION_COUNT}")
            log_update(f"[SPM] Retrying the benchmark with error correction {bm_iter+1}/{ERROR_CORRECTION_COUNT}")
            new_options, db_bench_args, reasoning, changed_value_dict = error_correction_options_file_generation(options, db_bench_args, reasoning, changed_value_dict, benchmark_results.get('error'), bm_iter)
            return benchmark(db_path, new_options, output_file_dir, reasoning, changed_value_dict, iteration_count, previous_results, options_files, db_bench_args, bm_iter+1)

    # ERROR: unexpected error
    elif benchmark_results['data_speed'] is None:
        is_error = True
        log_update(f"[SPM] Benchmark failed, the error is: Data speed is None. Check DB save path")
        print("[SPM] Benchmark failed, the error is: ",
              "Data speed is None. Check DB save path")
        # Save incorrect options in a file
        store_db_bench_output(output_file_dir,
                              f"{ini_file_count}-incorrect_options.ini",
                              benchmark_results, options, reasoning, changed_value_dict)
        # Restore previous options_file
        with open(f"{OPTIONS_FILE_DIR}", "w") as f:
            f.write(options_files[-1][0])

        if bm_iter < ERROR_CORRECTION_COUNT:
            print(f"[SPM] Retrying the benchmark with error correction {bm_iter+1}/{ERROR_CORRECTION_COUNT}")
            log_update(f"[SPM] Retrying the benchmark with error correction {bm_iter+1}/{ERROR_CORRECTION_COUNT}")
            new_options, db_bench_args, reasoning, changed_value_dict = error_correction_options_file_generation(options, db_bench_args, reasoning, changed_value_dict, benchmark_results.get('error'), bm_iter)
            return benchmark(db_path, new_options, output_file_dir, reasoning, changed_value_dict, iteration_count, previous_results, options_files, db_bench_args, bm_iter+1)

    else:
        is_error = False

        # Store the output of db_bench in a file
        store_db_bench_output(output_file_dir, f"{ini_file_count}.ini",
                              benchmark_results, options, reasoning, changed_value_dict)
        plot_2axis(*benchmark_results["ops_per_second_graph"],
                   f"Ops Per Second - {benchmark_results['ops_per_sec']}",
                   f"{output_file_dir}/ops_per_sec_{ini_file_count}.png")
        log_update(f"[SPM] Latest result: {benchmark_results['data_speed']}"
                        f"{benchmark_results['data_speed_unit']} and {benchmark_results['ops_per_sec']} ops/sec.")
        log_update(f"[SPM] Avg CPU and Memory usage: {average_cpu_usage}% and {average_memory_usage}%")
        print(
            f"[SPM] Latest result: {benchmark_results['data_speed']}",
            f"{benchmark_results['data_speed_unit']} and {benchmark_results['ops_per_sec']} ops/sec.",
            f"\n[SPM] Avg CPU and Memory usage: {average_cpu_usage}% and {average_memory_usage}%"
        )

    return is_error, benchmark_results, average_cpu_usage, average_memory_usage, options
