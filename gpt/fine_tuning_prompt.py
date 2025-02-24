from abstraction.abstraction import convert_dicts_to_randomdb, convert_options_to_randomdb
from gpt.gpt_request import request_gpt
from gpt.prompts_generator import generate_benchmark_info
from options_files.ops_options_file import cleanup_options_file
from trace_analyzer.analyzer import analyze_tracefile
from utils.constants import ABSTRACTION, FIO_RESULT_PATH, VERSION, RAG
from utils.system_operations.fio_runner import get_fio_result
from utils.system_operations.get_sys_info import system_info
from utils.utils import path_of_db


def generate_fine_tuning_options(fine_tuning_options, db_bench_args, changed_value_dict):
    if ABSTRACTION:
        fine_tuning_options = convert_options_to_randomdb(fine_tuning_options)
        changed_value_dict = convert_dicts_to_randomdb(changed_value_dict)

    db_path = path_of_db()
    fio_result = get_fio_result(FIO_RESULT_PATH)
    device_info = system_info(db_path, fio_result)
    trace_result = analyze_tracefile(db_path + "/tracefile")

    if ABSTRACTION:
        system_content = (
            "You are a really familiar with Log Structured Merge Tree based Key "
            "Value Store databases. We found some new database called LuminaStore and "
            "it is an LSM based KVS. You are being consulted help improve LuminaStore performance. "
            "Try to explain the reasoning behind the changed option, and only change 10 options. "
        )
    else:
        system_content = (
            "You are a RocksDB Expert. "
            "You are being consulted by a company to help improve their RocksDB performance "
            "by fine tuning the options they give. "
            "Please always refer to the device information and the workload information "
            "when generate a new options. "
        )

    user_contents = []
    assistant_contents = []
    
    benchmark_line = generate_benchmark_info(None, fine_tuning_options[0][2], fine_tuning_options[0][3], fine_tuning_options[0][4])
    options_string = "\n".join(f"{k}={v}" for k, v in changed_value_dict.items())
    
    if ABSTRACTION:
        user_contents.append((
            f"My device have {device_info}\n"
            f"The workload summary of the tracefile is: {trace_result}\n\n"
            # f"This is the current option:\n```\n{fine_tuning_options[0][0]}\n```\n"
            f"With that option, I got benchmark result of {benchmark_line}\n\n"
            "The options I want you to fine tune is only these:\n"
            f"```\n{options_string}\n```\n"
            "Whether increase or decrease one option affects other options.\n"
            "Aslo enclose the summary all changed options in ```"
        ))
    else:
        user_contents.append((
            f"I'm using RocksDB, on my device that have {device_info}\n"
            f"The workload summary of the tracefile is: {trace_result}\n\n"
            # f"This is the current option:\n```\n{fine_tuning_options[0][0]}\n```\n"
            f"With that option, I got benchmark result of {benchmark_line}\n\n"
            "The options I want you to fine tune is only these:\n"
            f"```\n{options_string}\n```\n"
            "Whether increase or decrease one option affects other options.\n"
            "Aslo enclose the summary all changed options in ```"
        ))

    for i in range(1, len(fine_tuning_options)):
        _, _, bench_res, cpuu, mmu, reason, change = fine_tuning_options[i]
        _, _, prev_bench_res, _, _, _, _ = fine_tuning_options[i-1]

        benchmark_line = generate_benchmark_info(None, bench_res, cpuu, mmu)
        if len(change.items()) > 0:
            options_string = "\n".join(f"{k}={v}" for k, v in change.items())
        else:
            options_string = "\n".join(k for k, v in changed_value_dict.items())

        assistant = (
            f"{reason}\n"
            f"```\n{options_string}\n```\n"
        )
        assistant_contents.append(assistant)

        if bench_res['ops_per_sec'] > prev_bench_res['ops_per_sec']:
            user_last_prompt = (
                "From the benchmark result, we can see the operation per second is increasing. "
                "Lets try another value on those changes! "
            )
        else:
            user_last_prompt = (
                "Seems like the operation per second is decreasing. "
                "Please refer to the previous changes and generate a new value to see the different! "
            )

        user = (
            f"With that changes, the benchmark result is {benchmark_line}\n\n"
            f"{user_last_prompt}"
            "Dont forget to enclose the summary all changed options in ```"
        )
        user_contents.append(user)

    matches = request_gpt(system_content, user_contents, assistant_contents, 0.4)

    clean_options_file = ""
    reasons = ""


    if matches is not None:
        clean_options_file, changes, db_bench_args = cleanup_options_file(matches.group(2), db_bench_args)
        reasons = matches.group(1) + matches.group(3)

    return clean_options_file, db_bench_args, reasons, changes
