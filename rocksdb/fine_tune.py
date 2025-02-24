import os
import rocksdb.subprocess_manager as spm
from gpt.fine_tuning_prompt import generate_fine_tuning_options
from rocksdb.parse_db_bench_output import parse_db_bench_output
from utils.constants import DB_BENCH_PATH, FINETUNE_ITERATION, OPTIONS_FILE_DIR, OUTPUT_PATH, TEST_NAME
from utils.graph import plot_2axis, plot_finetune
from utils.utils import log_update, store_db_bench_output

fine_tune_result = []

def fine_tuning(database_path, options, reasoning, changed_value_dict, previous_throughput, options_files, db_bench_args=[]):
    log_update("-"*50)
    log_update("[FNT] Start fine tuning")
    print("-"*50)
    print("[FNT] Start fine tuning")

    # Try initial option from GPT
    output, average_cpu_usage, average_memory_usage, options = spm.db_bench(
        DB_BENCH_PATH, database_path, options, 0, TEST_NAME, previous_throughput, options_files, db_bench_args)
    
    benchmark_results = parse_db_bench_output(output)

    # If error, throw to SPM
    if (benchmark_results.get("error") is not None) or (benchmark_results['data_speed'] is None):
        return output, average_cpu_usage, average_memory_usage, options, changed_value_dict
        # log_update("Fine tuner error! db_bench Benchmark failed!")
        # print("Fine tuner error! db_bench Benchmark failed!")
        # exit(1)
    
    # Save initial fine tuning option
    contents = os.listdir(OUTPUT_PATH)
    ini_file_count = len([f for f in contents if f.endswith(".ini")])

    output_file_dir = OUTPUT_PATH + f"/finetune-{ini_file_count}"
    os.makedirs(output_file_dir, exist_ok=True)

    store_db_bench_output(output_file_dir, "0.ini",
                            benchmark_results, options, reasoning, changed_value_dict)
    plot_2axis(*benchmark_results["ops_per_second_graph"],
                f"Ops Per Second - {benchmark_results['ops_per_sec']}",
                f"{output_file_dir}/ops_per_sec_0.png")
    
    # Add initial options and throughput
    fine_tuning_options = [(
        options, 
        output,
        benchmark_results, 
        average_cpu_usage, 
        average_memory_usage,
        reasoning,
        changed_value_dict
    )]

    for iter in range(1, FINETUNE_ITERATION+1):
        log_update(f"[FNT] Fine tuning iteration {iter}")
        print(f"[FNT] Fine tuning iteration {iter}")
        
        options, db_bench_args, reasons, changes = generate_fine_tuning_options(fine_tuning_options, db_bench_args, changed_value_dict)

        output, average_cpu_usage, average_memory_usage, options = spm.db_bench(
            DB_BENCH_PATH, database_path, options, 0, TEST_NAME, previous_throughput, options_files, db_bench_args)
        
        # Restore previous options_file
        with open(f"{OPTIONS_FILE_DIR}", "w") as f:
            f.write(options_files[-1][0])
        
        benchmark_results = parse_db_bench_output(output)

        # If error, hold up
        if (benchmark_results.get("error") is not None) or (benchmark_results['data_speed'] is None):
            log_update(f"[FNT] Fine tune error: {output_file_dir}/{iter}-incorrect_options.ini, the error is: {benchmark_results.get('error')}")
            print(f"[FNT] Fine tune error: {output_file_dir}/{iter}-incorrect_options.ini, the error is: {benchmark_results.get('error')}")
            
            # Save incorrect options in a file
            store_db_bench_output(output_file_dir, f"{iter}-incorrect_options.ini",
                                  benchmark_results, options, reasons, changes)
            
            # Restore previous options_file
            with open(f"{OPTIONS_FILE_DIR}", "w") as f:
                f.write(options_files[-1][0])
                
            continue

        store_db_bench_output(output_file_dir, f"{iter}.ini",
                              benchmark_results, options, reasons, changes)
        plot_2axis(*benchmark_results["ops_per_second_graph"],
                   f"Ops Per Second - {benchmark_results['ops_per_sec']}",
                   f"{output_file_dir}/ops_per_sec_{iter}.png")
        
        fine_tuning_options.append((
            options,
            output, 
            benchmark_results, 
            average_cpu_usage, 
            average_memory_usage,
            reasons, 
            changes
        ))
        
    # Plot finetune ops per sec
    if len(fine_tune_result) > 1:
        fine_tune_result.append([e[2]["ops_per_sec"] for e in fine_tuning_options])
        plot_finetune(fine_tune_result, f"Finetune OpsPerSec {TEST_NAME}", f"{OUTPUT_PATH}/Finetune_OpsPerSec.png")

    # Choose the best options
    options, output, _, average_cpu_usage, average_memory_usage, _, changed_value_dict = max(
        fine_tuning_options, key=lambda x: x[2]["ops_per_sec"])

    log_update("[FNT] Fine tuning done")
    log_update("-"*50)
    print("[FNT] Fine tuning done")
    print("-"*50)

    return output, average_cpu_usage, average_memory_usage, options, changed_value_dict
