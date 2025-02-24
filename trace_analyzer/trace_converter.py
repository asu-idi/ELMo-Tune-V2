import csv

def convert_txt_to_csv(input_file, output_file):
    
    """
    Convert a TXT file to a CSV file with specified columns.

    Parameters:
    input_file (str): The path to the input TXT file.
    output_file (str): The path to the output CSV file.
    columns (list): The list of column names for the CSV file.
    """

    # Column names as specified
    columns = [
        'get_access_count', 'get_unique_keys', 'get_key_size_average', 'get_key_size_median',
        'get_key_size_variance', 'get_value_size_average', 'get_value_size_median',
        'get_value_size_variance', 'get_mean', 'get_mode', 'get_median', 'get_quartiles[0]',
        'get_quartiles[2]', 'get_skewness', 'get_kurtosis', 'put_access_count', 'put_unique_keys',
        'put_key_size_average', 'put_key_size_median', 'put_key_size_variance', 'put_value_size_average',
        'put_value_size_median', 'put_value_size_variance', 'put_mean', 'put_mode', 'put_median',
        'put_quartiles[0]', 'put_quartiles[2]', 'put_skewness', 'put_kurtosis', 'delete_access_count',
        'delete_unique_keys', 'delete_key_size_average', 'delete_key_size_median', 'delete_key_size_variance',
        'delete_value_size_average', 'delete_value_size_median', 'delete_value_size_variance', 'delete_mean',
        'delete_mode', 'delete_median', 'delete_quartiles[0]', 'delete_quartiles[2]', 'delete_skewness',
        'delete_kurtosis', 'singledelete_access_count', 'singledelete_unique_keys',
        'singledelete_key_size_average', 'singledelete_key_size_median', 'singledelete_key_size_variance',
        'singledelete_value_size_average', 'singledelete_value_size_median', 'singledelete_value_size_variance',
        'singledelete_mean', 'singledelete_mode', 'singledelete_median', 'singledelete_quartiles[0]',
        'singledelete_quartiles[2]', 'singledelete_skewness', 'singledelete_kurtosis',
        'rangedelete_access_count', 'rangedelete_unique_keys', 'rangedelete_key_size_average',
        'rangedelete_key_size_median', 'rangedelete_key_size_variance', 'rangedelete_value_size_average',
        'rangedelete_value_size_median', 'rangedelete_value_size_variance', 'rangedelete_mean',
        'rangedelete_mode', 'rangedelete_median', 'rangedelete_quartiles[0]', 'rangedelete_quartiles[2]',
        'rangedelete_skewness', 'rangedelete_kurtosis', 'merge_access_count', 'merge_unique_keys',
        'merge_key_size_average', 'merge_key_size_median', 'merge_key_size_variance', 'merge_value_size_average',
        'merge_value_size_median', 'merge_value_size_variance', 'merge_mean', 'merge_mode', 'merge_median',
        'merge_quartiles[0]', 'merge_quartiles[2]', 'merge_skewness', 'merge_kurtosis',
        'iterator_seek_access_count', 'iterator_seek_unique_keys', 'iterator_seek_key_size_average',
        'iterator_seek_key_size_median', 'iterator_seek_key_size_variance', 'iterator_seek_value_size_average',
        'iterator_seek_value_size_median', 'iterator_seek_value_size_variance', 'iterator_seek_mean',
        'iterator_seek_mode', 'iterator_seek_median', 'iterator_seek_quartiles[0]', 'iterator_seek_quartiles[2]',
        'iterator_seek_skewness', 'iterator_seek_kurtosis', 'iterator_seekForPrev_access_count',
        'iterator_seekForPrev_unique_keys', 'iterator_seekForPrev_key_size_average',
        'iterator_seekForPrev_key_size_median', 'iterator_seekForPrev_key_size_variance',
        'iterator_seekForPrev_value_size_average', 'iterator_seekForPrev_value_size_median',
        'iterator_seekForPrev_value_size_variance', 'iterator_seekForPrev_mean', 'iterator_seekForPrev_mode',
        'iterator_seekForPrev_median', 'iterator_seekForPrev_quartiles[0]', 'iterator_seekForPrev_quartiles[2]',
        'iterator_seekForPrev_skewness', 'iterator_seekForPrev_kurtosis', 'multiget_access_count',
        'multiget_unique_keys', 'multiget_key_size_average', 'multiget_key_size_median',
        'multiget_key_size_variance', 'multiget_value_size_average', 'multiget_value_size_median',
        'multiget_value_size_variance', 'multiget_mean', 'multiget_mode', 'multiget_median',
        'multiget_quartiles[0]', 'multiget_quartiles[2]', 'multiget_skewness', 'multiget_kurtosis'
    ]

    # Read the data from the input file
    with open(input_file, 'r') as file:
        lines = file.readlines()

    # Write the data to a CSV file
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(columns)  # Write the header

        for line in lines:
            values = line.strip().split(',')
            writer.writerow(values)

def convert_txt_to_csv_windows(input_file, output_file):
    
    """
    Convert a TXT file to a CSV file with specified columns.

    Parameters:
    input_file (str): The path to the input TXT file.
    output_file (str): The path to the output CSV file.
    columns (list): The list of column names for the CSV file.
    """

    # Column names as specified
    columns = [
        'get_access_count', 'get_unique_keys', 'get_key_size_average', 'get_key_size_median', 'get_key_size_variance',
        'get_value_size_average', 'get_value_size_median', 'get_value_size_variance', 'get_mean', 'get_mode', 'get_median',
        'put_access_count', 'put_unique_keys', 'put_key_size_average', 'put_key_size_median', 'put_key_size_variance',
        'put_value_size_average', 'put_value_size_median', 'put_value_size_variance', 'put_mean', 'put_mode', 'put_median', 
        'delete_access_count', 'delete_unique_keys', 'delete_key_size_average', 'delete_key_size_median', 'delete_key_size_variance',
        'delete_value_size_average', 'delete_value_size_median', 'delete_value_size_variance', 'delete_mean', 'delete_mode', 'delete_median',
        'singledelete_access_count', 'singledelete_unique_keys', 'singledelete_key_size_average', 'singledelete_key_size_median', 
        'singledelete_key_size_variance', 'singledelete_value_size_average', 'singledelete_value_size_median', 'singledelete_value_size_variance',
        'singledelete_mean', 'singledelete_mode', 'singledelete_median', 
        'rangedelete_access_count', 'rangedelete_unique_keys', 'rangedelete_key_size_average', 'rangedelete_key_size_median', 
        'rangedelete_key_size_variance', 'rangedelete_value_size_average', 'rangedelete_value_size_median', 'rangedelete_value_size_variance',
        'rangedelete_mean', 'rangedelete_mode', 'rangedelete_median', 'merge_access_count', 'merge_unique_keys', 'merge_key_size_average',
        'merge_key_size_median', 'merge_key_size_variance', 'merge_value_size_average', 'merge_value_size_median', 'merge_value_size_variance',
        'merge_mean', 'merge_mode', 'merge_median', 
        'iterator_seek_access_count', 'iterator_seek_unique_keys', 'iterator_seek_key_size_average', 'iterator_seek_key_size_median',
        'iterator_seek_key_size_variance', 'iterator_seek_value_size_average', 'iterator_seek_value_size_median', 'iterator_seek_value_size_variance',
        'iterator_seek_mean', 'iterator_seek_mode', 'iterator_seek_median', 'iterator_seekForPrev_access_count', 'iterator_seekForPrev_unique_keys',
        'iterator_seekForPrev_key_size_average', 'iterator_seekForPrev_key_size_median', 'iterator_seekForPrev_key_size_variance', 
        'iterator_seekForPrev_value_size_average', 'iterator_seekForPrev_value_size_median', 'iterator_seekForPrev_value_size_variance',
        'iterator_seekForPrev_mean', 'iterator_seekForPrev_mode', 'iterator_seekForPrev_median', 
        'multiget_access_count', 'multiget_unique_keys', 'multiget_key_size_average', 'multiget_key_size_median', 'multiget_key_size_variance',
        'multiget_value_size_average', 'multiget_value_size_median', 'multiget_value_size_variance', 'multiget_mean', 'multiget_mode', 'multiget_median'
    ]

    # Read the data from the input file
    with open(input_file, 'r') as file:
        lines = file.readlines()

    # Write the data to a CSV file
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(columns)  # Write the header

        for line in lines:
            values = line.strip().split(',')
            writer.writerow(values)