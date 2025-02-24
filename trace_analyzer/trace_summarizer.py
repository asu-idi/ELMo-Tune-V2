import pandas as pd
from utils.constants import OUTPUT_PATH
import numpy as np
from scipy.optimize import curve_fit
from scipy.stats import zipf, uniform, norm, expon
import glob
import os

operations = ["get", "put", "delete", "singledelete", "rangedelete", "merge", "iterator_seek", "iterator_seekForPrev", "multiget"]

def count_total_queries(data):
    access_count_columns = data.filter(like='_access_count').columns
    total_queries = data[access_count_columns].sum(axis=1).sum()
    return total_queries

def count_percentages(data):
    access_count_columns = data.filter(like='_access_count').columns
    column_sums = data[access_count_columns].sum()
    total_access_count = column_sums.sum()
    column_percentages = (column_sums / total_access_count) * 100
    rename_dict = {col: col.replace('_access_count', '').capitalize() for col in access_count_columns}
    column_percentages.rename(index=rename_dict, inplace=True)
    non_zero_percentages = column_percentages[column_percentages > 0]
    return non_zero_percentages

def convert_output(query_type):
    if query_type == 'Get':
        return 'Read'
    elif query_type == 'Put':
        return 'Write'
    elif query_type == 'Merge':
        return 'Merge/read-modify-write'
    else:
        return query_type

def profile_query_composition(data):
    if len(data) == 1:
        dominant_query = next(iter(data.items()))
        workload_type = f"{convert_output(dominant_query)} only"
    elif all(45 <= data.get(i, 0) <= 55 for i in [0, 1]):
        workload_type = "heavy updating"
    else:
        max_type = data.idxmax()
        workload_type = f"{convert_output(max_type)} heavy"
    return workload_type

def analyze_detailed_access_distribution(data):
    descriptions = []

    for op in operations:
        mean_key = f'{op}_mean'
        mode_key = f'{op}_mode'
        median_key = f'{op}_median'
        quartile1_key = f'{op}_quartiles[0]'
        quartile3_key = f'{op}_quartiles[2]'
        kurtosis_key = f'{op}_kurtosis'

        if mean_key in data.columns:
            mean = data[mean_key].iloc[0]
            mode = data[mode_key].iloc[0]
            median = data[median_key].iloc[0]
            quartile1 = data[quartile1_key].iloc[0] if quartile1_key in data.columns else None
            quartile3 = data[quartile3_key].iloc[0] if quartile3_key in data.columns else None
            kurtosis = data[kurtosis_key].iloc[0] if kurtosis_key in data.columns else None
            
            if mode == 0:
                continue
            
            description = f"For {op} requests:\n"
            description += f"  - The mean, median, and mode of accesses per key is {mean:.3f}, {mode}, and {median} respectively.\n"
            if (quartile1 is not None) and (quartile3 is not None):
                description += f"  - The first quartile (25%) is {quartile1}, and the third quartile (75%) is {quartile3}.\n"
            if kurtosis is not None:
                description += f"  - The kurtosis of the distribution is {kurtosis:.3f}. "

            # if mode == 1:
            #     description += "This suggests that most keys are accessed once, indicating a workload where keys are typically accessed uniquely per session or period.\n"
            # elif mean < 2:
            #     description += "This suggests a fairly even distribution with most keys accessed only a few times.\n"
            # else:
            #     description += "This suggests that some keys may be accessed multiple times, indicating potential hotspots.\n"

            descriptions.append(description)
    
    return descriptions

def profile_size(data):
    messages = []

    for operation in operations:
        value_size_average_col = f"{operation}_value_size_average"
        value_size_median_col = f"{operation}_value_size_median"
        value_size_variance_col = f"{operation}_value_size_variance"

        key_size_average_col = f"{operation}_key_size_average"
        key_size_median_col = f"{operation}_key_size_median"
        key_size_variance_col = f"{operation}_key_size_variance"

        gen_message = f"For {operation} operations: "
        messages.append(gen_message)

        if key_size_average_col in data.columns and key_size_median_col in data.columns and key_size_variance_col in data.columns:
            key_average = data[key_size_average_col].mean(skipna=True)
            key_median = data[key_size_median_col].mean(skipna=True)
            key_variance = data[key_size_variance_col].mean(skipna=True)

            if key_average > 0:
                if key_variance == 0:
                    key_message = (
                        f"Average key size is {key_average:.2f} bytes with 0 variance."
                    )
                else:
                    key_message = (
                        f"Average key size is {key_average:.2f} bytes with a larger variance (around {key_variance:.2f})."
                    )
                messages.append(key_message)
        
        if value_size_average_col in data.columns and value_size_median_col in data.columns and value_size_variance_col in data.columns:
            average = data[value_size_average_col].mean(skipna=True)
            median = data[value_size_median_col].mean(skipna=True)
            variance = data[value_size_variance_col].mean(skipna=True)

            if average > 0 and median > 0:
                if variance == 0:
                    message = (
                        f"Average value size is {average:.2f} bytes, with the median also at {median:.2f} bytes and zero variance."
                    )
                else:
                    message = (
                        f"Average value size is {average:.2f} bytes with a larger variance (around {variance:.2f})."
                    )
                messages.append(message)

    return messages

def generate_summary(csv_file_path):
    data = pd.read_csv(csv_file_path, index_col=False)
    cf_num = 1
    
    non_zero_percentages = count_percentages(data)
    key_value_sizes_message = "".join(f"{message}\n" for message in profile_size(data))
    key_access_message = "".join(f"{message}\n" for message in analyze_detailed_access_distribution(data))

    query_composition = (
        "The workload consists of interleaved "
        + ", ".join(f"{value:.2f}% {index}" for index, value in non_zero_percentages.items())
        + f". There are {cf_num} column family in this workload.\n"
    )

    summary = (
        "The workload information is as follows:\n"
        "1. Query Compositions\n"
        f"{query_composition}"
        "2. Key and Value Size Characteristics\n"
        f"{key_value_sizes_message}"
        "3. Key access distribution\n"
        f"{key_access_message}"
    )

    return summary

def read_data(file_path):
    access_count = []
    frequency = []
    with open(file_path, 'r') as file:

        # Check if the file is empty
        if not file.read(1):
            return [], []

        for line in file:
            parts = line.strip().split()

            # Hardcoded for now. Must be changed in the future for a general solution
            if len(parts) == 4:
                # Key distribution has 4 parts
                access_count.append(int(parts[1]))
                frequency.append(int(parts[3]))
            elif len(parts) == 2:
                # Key Size distribution has 2 parts
                access_count.append(int(parts[0]))
                frequency.append(int(parts[1]))
            elif len(parts) == 6:
                # Value Size distribution has 6 parts
                access_count.append(int(parts[3]))
                frequency.append(int(parts[5]))

    return np.array(access_count), np.array(frequency)

def fit_distribution(data_file):
    # Load data
    access_count, frequency = read_data(data_file)

    if len(access_count) == 0:
        return "Does not contain any data points.", [access_count, frequency]
    elif len(access_count) == 1:
        return "Contains only one data point. Uniform distribution.", [access_count, frequency]
    elif len(access_count) < 5:
        # This is effectively the prompt to the LLM
        return "Identify and leverage the patttern based on the access distribution that we provide next", [access_count, frequency]

    # Normalize frequencies to create a probability distribution
    frequency_normalized = frequency / np.sum(frequency)

    # Define the two-term exponential function
    def two_term_exponential(x, a, b, c, d):
        return a * np.exp(b * x) + c * np.exp(d * x)

    # Fit the data to the two-term exponential model
    initial_guess = [1.0, 1.0, 1.0, 1.0]
    popt_exp, _ = curve_fit(two_term_exponential, access_count, frequency_normalized, p0=initial_guess, maxfev=100000)

    # Fit Uniform distribution
    uniform_start, uniform_width = uniform.fit(access_count, floc=0)

    # Fit Gaussian (Normal) distribution
    mu, sigma = norm.fit(access_count)

    # Fit Exponential distribution
    loc_exp, scale_exp = expon.fit(access_count, floc=0)

    # Fit and evaluate Zipfian distribution for different theta values
    def fit_zipf(x, s):
        return zipf.pmf(x, s) / np.sum(zipf.pmf(np.arange(1, len(x) + 1), s))

    theta_values = [0.5, 0.8, 1.0, 1.2, 1.5, 1.8, 2.0, 2.5, 3.0]
    metrics_zipf = {}
    for theta in theta_values:
        y_fit_zipf = fit_zipf(access_count, theta)
        r_squared = 1 - np.sum((frequency_normalized - y_fit_zipf) ** 2) / np.sum((frequency_normalized - np.mean(frequency_normalized)) ** 2)
        rmse = np.sqrt(np.mean((frequency_normalized - y_fit_zipf) ** 2))
        metrics_zipf[theta] = {'R^2': r_squared, 'RMSE': rmse}

    # Calculate goodness-of-fit metrics
    def calculate_r_squared(y_true, y_pred):
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        return 1 - (ss_res / ss_tot)

    def calculate_rmse(y_true, y_pred):
        return np.sqrt(np.mean((y_true - y_pred) ** 2))

    # Predicted values for access_count
    y_pred_exp = two_term_exponential(access_count, *popt_exp)
    y_pred_uniform = uniform.pdf(access_count, uniform_start, uniform_width)
    y_pred_gauss = norm.pdf(access_count, mu, sigma)
    y_pred_expon = expon.pdf(access_count, loc_exp, scale_exp)

    # Fitness metrics for each distribution
    metrics = {
        'Two-Term Exponential': {
            'R^2': calculate_r_squared(frequency_normalized, y_pred_exp),
            'RMSE': calculate_rmse(frequency_normalized, y_pred_exp)
        },
        'Uniform': {
            'R^2': calculate_r_squared(frequency_normalized, y_pred_uniform),
            'RMSE': calculate_rmse(frequency_normalized, y_pred_uniform)
        },
        'Gaussian': {
            'R^2': calculate_r_squared(frequency_normalized, y_pred_gauss),
            'RMSE': calculate_rmse(frequency_normalized, y_pred_gauss)
        },
        'Exponential': {
            'R^2': calculate_r_squared(frequency_normalized, y_pred_expon),
            'RMSE': calculate_rmse(frequency_normalized, y_pred_expon)
        }
    }

    # Combine Zipfian metrics
    for theta, zipf_metrics in metrics_zipf.items():
        metrics[f'Zipf (theta={theta})'] = zipf_metrics

    # Identify the best fit
    best_fit = min(metrics.items(), key=lambda item: item[1]['RMSE'])

    return best_fit[0], [access_count, frequency]

def generate_pattern_message_from_trace(pattern_name):
    # Define the file path pattern
    operations = [
        "get", "put", "delete", "singledelete", "rangedelete", 
        "merge", "iterator_seek", "iterator_seekForPrev", "multiget"
    ]

    filename_pattern = f"{OUTPUT_PATH}/trace_data/*accessed_{pattern_name}_distribution.txt"
    
    # Find all matching files
    txt_files = glob.glob(filename_pattern)
    
    # Dictionary to store results
    results = {}
    pattern_info_dict = {}

    # Process each file
    # Process each file and map to operations
    for txt_file in txt_files:
        operation_matched = None
        for operation in operations:
            if operation in os.path.basename(txt_file).lower():
                operation_matched = operation
                break
        
        if operation_matched:
            acc, freq = read_data(txt_file)
            pattern_info_dict[operation_matched] = [acc, freq]

            try:
                best_fit, _ = fit_distribution(txt_file)
                results[operation_matched] = best_fit
            except Exception as e:
                results[operation_matched] = f"Error: {str(e)}"
        else:
            # Handle cases where no operation matches (optional)
            results[txt_file] = "Operation not matched"

    return results, pattern_info_dict

def generate_summary_row(row, column_names):
    # Convert the row to a DataFrame with a single row to work with existing functions
    data = pd.DataFrame([row], columns=column_names)

    # Extract necessary values for summary
    non_zero_percentages = count_percentages(data)
    key_value_sizes_message = "".join(f"{message}\n" for message in profile_size(data))
    # key_access_message = "".join(f"{message}\n" for message in analyze_detailed_access_distribution(data))
    # key_access_message = 
    cf_num = 1  # Update logic if needed

    query_composition = (
        "The workload consists of interleaved "
        + ", ".join(f"{value:.2f}% {index}" for index, value in non_zero_percentages.items())
        + f". There are {cf_num} column family in this workload.\n"
    )

    summary = (
        # "The workload information is as follows:\n"
        f"Query Compositions: {query_composition}"
        # f"Key and Value Size Characteristics: {key_value_sizes_message}"
        # f"Key access distribution: {key_access_message}"
    )

    return summary

def generate_summary_windows(csv_file_path):
    # Read the CSV file
    data = pd.read_csv(csv_file_path, index_col=False)

    # Get column names
    column_names = data.columns.tolist()

    key_access_message, key_access_pattern_info_dict = generate_pattern_message_from_trace("key_count")
    key_size_message, key_size_pattern_info_dict = generate_pattern_message_from_trace("key_size")
    value_size_message, value_size_pattern_info_dict = generate_pattern_message_from_trace("value_size")

    # Dictionary to store summaries
    summaries = ["The workload information is as follows:\n"]
    for operation, result in key_access_message.items():
        summaries.append(f"Operation: {operation}, Key Access Distribution: {result}\n")
        summaries.append("The pattern is as follows:\n")
        summaries.append(f"Access Count: {key_access_pattern_info_dict[operation][0]}\n")
        summaries.append(f"Frequency: {key_access_pattern_info_dict[operation][1]}\n")

    for operation, result in key_size_message.items():
        summaries.append(f"Operation: {operation}, Key Size Distribution: {result}\n")
        summaries.append("The pattern is as follows:\n")
        summaries.append(f"Key Size (bytes): {key_size_pattern_info_dict[operation][0]}\n")
        summaries.append(f"Frequency: {key_size_pattern_info_dict[operation][1]}\n")

    for operation, result in value_size_message.items():
        summaries.append(f"Operation: {operation}, Value Size Distribution: {result}\n")
        summaries.append("The pattern is as follows:\n")
        summaries.append(f"Value Size (bytes) Ceiling: {value_size_pattern_info_dict[operation][0]}\n")
        summaries.append(f"Frequency: {value_size_pattern_info_dict[operation][1]}\n")
   
    summaries.append(f"The benchmark running time is: {len(data)*10} seconds.\n")

    # summaries.append("\n\nHere is the converted string from the csv file:\n")
    # summaries.append("Each time window equals to 10 seconds.\n")

    # # Iterate through each row and generate summaries
    # time_index=0
    # for index, row in data.iterrows():
    #     row_summary = generate_summary_row(row, column_names)
    #     summaries.append(f"Time window {time_index}:{row_summary}\n")
    #     time_index+= 1

    return "".join(summaries)
