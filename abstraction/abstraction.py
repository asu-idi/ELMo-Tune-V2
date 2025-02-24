from abstraction.dictionary import OPTION_MAP

def convert_options_to_randomdb(options):
    converted = []

    for option in options:
        option_list = list(option)
        converted_options = []

        for line in option_list[0].splitlines():
            if not line.strip() or '=' not in line:
                continue

            key, value = map(str.strip, line.split('=', 1))

            if key in OPTION_MAP:
                converted_key = OPTION_MAP[key]
                converted_options.append(f"{converted_key} = {value}")

        option_list[0] = "\n".join(converted_options)

        if len(option_list) >= 7 and option_list[6]:
            option_list[6] = convert_dicts_to_randomdb(option_list[6])

        converted.append(tuple(option_list))
    
    return converted

def convert_dicts_to_randomdb(options):
    converted = {}

    for key, value in options.items():
        if key in OPTION_MAP:
            converted_key = OPTION_MAP[key]
            converted[converted_key] = value
    
    return converted

def convert_options_to_rocksdb(converted_options):
    reverse_option_map = {new_key: old_key for old_key, new_key in OPTION_MAP.items()}
    original_options = []

    for line in converted_options.splitlines():
        if not line.strip() or '=' not in line:
            continue

        key, value = map(str.strip, line.split('=', 1))
        
        if key in reverse_option_map:
            original_key = reverse_option_map[key]
            original_options.append(f"{original_key} = {value}")
        elif key in OPTION_MAP:
            original_options.append(f"{key} = {value}")
    
    return "\n".join(original_options)
