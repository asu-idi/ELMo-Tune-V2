import mmap
import os
import struct
import re
import time

from utils.utils import log_update

mmap_file_path = "/tmp/mmap_file.mmap"
mmap_size = 1024

def create_mmap_file():
    if not(os.path.exists(mmap_file_path)):
        with open(mmap_file_path, "wb") as f:
            f.write(b'\x00' * mmap_size)
    else:
        log_update("MMap file already exists. Setting top bit to 0 to avoid db_bench reads.")
        with open(mmap_file_path, "r+b") as f:
            with mmap.mmap(f.fileno(), mmap_size, access=mmap.ACCESS_WRITE) as m:
                m[0] = 0

def add_mmap_file_to_option(option_file, mmap_str):
    '''
    Add the mmap file path to the option string
    '''
    pattern = re.compile(r'(\w+)\s*=\s*([\w\.\-]+)')
    
    # Convert mmap_str to a dictionary
    mmap_options = {}
    for match in pattern.finditer(mmap_str):
        key, value = match.groups()
        mmap_options[key] = value
    
    # Update option_file line by line
    updated_lines = []
    for line in option_file.split('\n'):
        match = pattern.match(line)
        if match:
            key, _ = match.groups()
            if key in mmap_options:
                line = f"{key} = {mmap_options[key]}"
        updated_lines.append(line)
    
    updated_option_file = '\n'.join(updated_lines)
    
    return updated_option_file

def convert_option_string_to_list(data):
    '''
    Convert the string to a mmap specific list of integers
    '''
    dataKey = [
        'max_open_files', 
        'max_total_wal_size', 
        'delete_obsolete_files_period_micros', # Currently ignored
        'max_background_jobs', 
        'max_background_compactions', 
        'max_subcompactions', 
        'stats_dump_period_sec', 
        'compaction_readahead_size', 
        'writable_file_max_buffer_size', 
        'bytes_per_sync', 
        'wal_bytes_per_sync', 
        'delayed_write_rate', 
        'avoid_flush_during_shutdown', 
        'write_buffer_size', 
        'compression', 
        'level0_file_num_compaction_trigger', 
        'max_bytes_for_level_base', 
        'disable_auto_compactions', 
        'memtable_max_range_deletions', 
    ]
    
    # Extract key-value pairs from the input string using regex
    options = {}
    pattern = re.compile(r'(\w+)\s*=\s*([\w\.\-]+)')
    for match in pattern.finditer(data):
        key, value = match.groups()
        options[key] = value
    
    # Create the list of values based on dataKey
    result = []
    for key in dataKey:
        if key in options:
            if options[key].lower() == 'false':
                value = 0
            elif options[key].lower() == 'true':
                value = 1
            elif 'no' in options[key].lower():
                value = 0
            elif 'snappy' in options[key].lower():
                value = 1
            elif 'zlib' in options[key].lower():
                value = 2
            elif 'bzip2' in options[key].lower():
                value = 3
            elif 'lz4' in options[key].lower():
                value = 4
            elif 'lz4hc' in options[key].lower():
                value = 5
            elif 'xpress' in options[key].lower():
                value = 6
            elif 'zstd' in options[key].lower():
                value = 7
            else:
                try:
                    value = int(options[key])
                    if not(-2147483648 <= value <= 2147483647):
                        log_update(f"Value for {key} is out of boundaries: {value}. Clamping applied.")
                        value = max(-2147483648, min(2147483647, value))
                except:
                    log_update(f"Error converting value of {key} to integer: " + options[key])
                    log_update("Forcing value to 0 for key: " + key)
                    value = 0
        else:
            log_update("Error key not found in options file: " + key)
            log_update("Forcing value to 0 for key: " + key)
            value = 0  # Default value if key is not found
        
        result.append(value)
    
    return result

def write_to_mmap_file(data):
    '''
    The file is memory mapped and we do not perform any error checking. 
    All operations are type and order sensistive.
    The data is written in the following order:
        int max_open_file = *reinterpret_cast<int*>(mmap_dynamic_file_addr_ + 1);
        int max_total_wal_size = *reinterpret_cast<int*>(mmap_dynamic_file_addr_ + 5);
        int delete_obsolete_files_period_micros = *reinterpret_cast<int*>(mmap_dynamic_file_addr_ + 9);
        int max_background_jobs = *reinterpret_cast<int*>(mmap_dynamic_file_addr_ + 13);
        int max_background_compactions = *reinterpret_cast<int*>(mmap_dynamic_file_addr_ + 17);
        int max_subcompactions = *reinterpret_cast<int*>(mmap_dynamic_file_addr_ + 21);
        int stats_dump_period_sec = *reinterpret_cast<int*>(mmap_dynamic_file_addr_ + 25);
        int compaction_readahead_size = *reinterpret_cast<int*>(mmap_dynamic_file_addr_ + 29);
        int writable_file_max_buffer_size = *reinterpret_cast<int*>(mmap_dynamic_file_addr_ + 33);
        int bytes_per_sync = *reinterpret_cast<int*>(mmap_dynamic_file_addr_ + 37);
        int wal_bytes_per_sync = *reinterpret_cast<int*>(mmap_dynamic_file_addr_ + 41);
        int delayed_write_rate = *reinterpret_cast<int*>(mmap_dynamic_file_addr_ + 45);
        int avoid_flush_during_shutdown = *reinterpret_cast<int*>(mmap_dynamic_file_addr_ + 49);

        int write_buffer_size = *reinterpret_cast<int*>(mmap_dynamic_file_addr_ + 53);
        int compression = *reinterpret_cast<int*>(mmap_dynamic_file_addr_ + 57);
        int level0_file_num_compaction_trigger = *reinterpret_cast<int*>(mmap_dynamic_file_addr_ + 61);
        int max_bytes_for_level_base = *reinterpret_cast<int*>(mmap_dynamic_file_addr_ + 65);
        int disable_auto_compactions = *reinterpret_cast<int*>(mmap_dynamic_file_addr_ + 69);
        int memtable_max_range_deletions = *reinterpret_cast<int*>(mmap_dynamic_file_addr_ + 73);
    '''

    if type(data) == str:
        data = convert_option_string_to_list(data)
    
    with open(mmap_file_path, "r+b") as f:
        with mmap.mmap(f.fileno(), mmap_size, access=mmap.ACCESS_WRITE) as m:
            
            # Set ready flag to 0 while writing
            m[0] = 0 

            # Write compaction speed and cache size after the flag
            m.seek(1)  # Move to position 1 after the flag byte
            for i in range(len(data)):
                m.write(struct.pack('i', data[i]))

            m[0] = 1  # Flag to indicate "ready"

# create_mmap_file()
# data = [
#     -1, # max_open_files
#     0, # max_total_wal_size
#     216, # delete_obsolete_files_period_micros ->  Currently Ignored
#     2, # max_background_jobs
#     -1, # max_background_compactions
#     1, # max_subcompactions
#     600, # stats_dump_period_sec
#     2097152, # compaction_readahead_size
#     1048576, # writable_file_max_buffer_size
#     0, # bytes_per_sync
#     0, # wal_bytes_per_sync
#     8388608, # delayed_write_rate
#     0, # avoid_flush_during_shutdown
#     67108864, # write_buffer_size
#     0, # compression
#     4, # level0_file_num_compaction_trigger
#     268435456, # max_bytes_for_level_base
#     0, # disable_auto_compactions
#     0 # memtable_max_range_deletions
# ]
# write_to_mmap_file(data)
