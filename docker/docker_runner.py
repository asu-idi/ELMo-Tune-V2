import docker
from dotenv import load_dotenv
import os
import threading

load_dotenv()

client = docker.from_env()

def main():
    '''
    Main function to run multiple docker containers one after the other. All containers mount a volume to the host machine.
    Additionally, before mounting, the environment variables are updated to reflect the current iteration number and the status 
    of the for loop which is controlling the memory and cpus. 
    '''
    # Devices and their mounting points on local machine
    devices_mounting = {
        "hdd": "/media/ken/HDD",
        # "ssd": "/media/ken/Disk",
    }

    threads = []

    for device, mount in devices_mounting.items():
        t = threading.Thread(target=run_on_device, args=(device, mount))
        threads.append(t)
    
    print("Starting on all devices")

    for t in threads:
        t.start()
    
    for t in threads:
        t.join()

    print("All benchmarks test completed")

def run_on_device(device, mount):
    cpu_list = [2] # CPU list
    memory_list = [4] # Memory list

    docker_image = "llm-dynopts" # Docker image name
    base_db_path = f"{docker_image}/dbr" # Base path for mounting
    
    # Tests case and their environment variables
    tests = {
        "fillrandom_1_finetune": [
            "TEST_NAME=fillrandom",
            "DURATION=600",
            "CASE_NUMBER=1",
            "FINETUNE_ITERATION=3",
        ],
        "fillrandom_2_finetune": [
            "TEST_NAME=fillrandom",
            "DURATION=600",
            "CASE_NUMBER=2",
            "FINETUNE_ITERATION=3",
        ],
        "fillrandom_3_finetune": [
            "TEST_NAME=fillrandom",
            "DURATION=600",
            "CASE_NUMBER=3",
            "FINETUNE_ITERATION=3",
        ],
        "fillrandom_4_finetune": [
            "TEST_NAME=fillrandom",
            "DURATION=600",
            "CASE_NUMBER=4",
            "FINETUNE_ITERATION=3",
        ],
        "fillrandom_1_finetune_dynopts": [
            "TEST_NAME=fillrandom",
            "DURATION=600",
            "CASE_NUMBER=1",
            "FINETUNE_ITERATION=3",
            "DYNAMIC_OPTION_TUNING=true",
        ],
        "fillrandom_2_finetune_dynopts": [
            "TEST_NAME=fillrandom",
            "DURATION=600",
            "CASE_NUMBER=2",
            "FINETUNE_ITERATION=3",
            "DYNAMIC_OPTION_TUNING=true",
        ],
        "fillrandom_3_finetune_dynopts": [
            "TEST_NAME=fillrandom",
            "DURATION=600",
            "CASE_NUMBER=3",
            "FINETUNE_ITERATION=3",
            "DYNAMIC_OPTION_TUNING=true",
        ],
        "fillrandom_4_finetune_dynopts": [
            "TEST_NAME=fillrandom",
            "DURATION=600",
            "CASE_NUMBER=4",
            "FINETUNE_ITERATION=3",
            "DYNAMIC_OPTION_TUNING=true",
        ],
    }

    for memory_cap in memory_list:
        for cpu_cap in cpu_list:
            for test, env in tests.items():
                print("-" * 50)
                print(f"Running Iteration for CPU: {cpu_cap} Memory: {memory_cap} on /{device} for {test}")

                # Run docker container with mount and environment variables as in cpu and memory
                container = client.containers.run(
                    f"{docker_image}:latest", 
                    detach=True, 
                    name=f"{docker_image}_c{cpu_cap}_m{memory_cap}_{device}_{test}",
                    environment=[
                        # Default environment variables
                        f"DB_PATH=/{device}/{base_db_path}/c{cpu_cap}_m{memory_cap}_{test}",
                        f"OUTPUT_PATH=/{device}/{base_db_path}/c{cpu_cap}_m{memory_cap}_{test}_output",
                        f"DEVICE={device}",
                        f"OPENAI_API_KEY={os.getenv('OPENAI_API_KEY')}",
                        "ITERATION_COUNT=3",
                    ] + env,
                    cpu_count=cpu_cap,
                    cpu_quota=cpu_cap*100000,
                    mem_limit=f"{memory_cap}g", 
                    volumes={
                        f"{mount}/{docker_image}": {'bind': f'/{device}/{base_db_path}', 'mode': 'rw'},
                    }
                )

                # Wait for the container to finish and log the output
                container.wait()

                # Get the logs of the container
                log_output = container.logs().decode('utf-8')
                
                log_file_path = f"output/{container.name}.txt"
                os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
                
                with open(log_file_path, 'w') as log_file:
                    log_file.write(log_output)
                
                # Remove the container
                container.remove()

if __name__ == "__main__":
    main()
