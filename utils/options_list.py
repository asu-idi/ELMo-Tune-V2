import json
from copy import deepcopy
from typing import Optional, Type, Any, Tuple, List, Union
from pydantic import BaseModel, create_model
from pydantic.fields import FieldInfo

from utils.filter import DB_BENCH_ARGS


def make_field_optional(model: Type[BaseModel]):
    '''
    Function to make all the fields in the model optional. Works with nested models.
    Source: https://stackoverflow.com/questions/67699451/make-every-field-as-optional-with-pydantic/

    Parameters:
    - model (Type[BaseModel]): The model to make optional

    Returns:
    - model (Type[BaseModel]): The model with all fields optional
    '''
    def convert_to_optional(field: FieldInfo, default: Any = None) -> Tuple[Any, FieldInfo]:
        '''
        Function to convert a field to optional

        Parameters:
        - field (FieldInfo): The field to convert
        - default (Any): The default value

        Returns:
        - Tuple[Any, FieldInfo]: The converted field
        '''
        new = deepcopy(field)
        new.default = default

        # If the field annotation is a subclass of BaseModel, recursively make its fields optional.
        field_type = field.annotation
        if isinstance(field_type, type) and issubclass(field_type, BaseModel):
            field_type = make_field_optional(field_type)

        # Update the annotation to be optional
        new.annotation = Union[field_type, type(None)]  # type: ignore
        return new.annotation, new
    
    return create_model(
        f'Optional{model.__name__}',
        __base__=model,
        __module__=model.__module__,
        **{
            field_name: convert_to_optional(field_info)
            for field_name, field_info in model.model_fields.items()
        }
    )

# TODO: Dynamic model creation for DB_BENCH_ARGS
# DBBenchOptions = create_model(
#     "DBBenchOptions",
#     __base__=BaseModel,
#     **{bench_key: (str, None) for bench_key in DB_BENCH_ARGS}
# )
class DBBenchOptions(BaseModel):
    cache_size: int
    bloom_bits: int
    use_ribbon_filter: str
    row_cache_size: int
    cache_numshardbits: int
    enable_io_prio: str
    enable_cpu_prio: str
    file_checksum: str
    use_keep_filter: str
    

class Version(BaseModel):
    rocksdb_version: str
    options_file_version: str


class DBOptions(BaseModel):
    max_background_flushes: int
    compaction_readahead_size: int
    wal_bytes_per_sync: int
    bytes_per_sync: int
    max_open_files: int
    stats_history_buffer_size: int
    stats_dump_period_sec: int
    stats_persist_period_sec: int
    delete_obsolete_files_period_micros: int
    max_total_wal_size: int
    strict_bytes_per_sync: str
    delayed_write_rate: int
    avoid_flush_during_shutdown: str
    writable_file_max_buffer_size: int
    max_subcompactions: int
    max_background_compactions: int
    max_background_jobs: int
    lowest_used_cache_tier: str
    bgerror_resume_retry_interval: int
    max_bgerror_resume_count: int
    best_efforts_recovery: str
    write_dbid_to_manifest: str
    avoid_unnecessary_blocking_io: str
    atomic_flush: str
    log_readahead_size: int
    dump_malloc_stats: str
    info_log_level: str
    write_thread_max_yield_usec: int
    max_write_batch_group_size_bytes: int
    wal_compression: str
    write_thread_slow_yield_usec: int
    enable_pipelined_write: str
    persist_stats_to_disk: str
    max_manifest_file_size: int
    WAL_size_limit_MB: int
    fail_if_options_file_error: str
    max_log_file_size: int
    manifest_preallocation_size: int
    listeners: str
    log_file_time_to_roll: int
    allow_data_in_errors: str
    WAL_ttl_seconds: int
    recycle_log_file_num: int
    file_checksum_gen_factory: str
    keep_log_file_num: int
    db_write_buffer_size: int
    table_cache_numshardbits: int
    use_adaptive_mutex: str
    allow_ingest_behind: str
    skip_checking_sst_file_sizes_on_db_open: str
    random_access_max_buffer_size: int
    access_hint_on_compaction_start: str
    allow_concurrent_memtable_write: str
    track_and_verify_wals_in_manifest: str
    skip_stats_update_on_db_open: str
    compaction_verify_record_count: str
    paranoid_checks: str
    max_file_opening_threads: int
    verify_sst_unique_id_in_manifest: str
    avoid_flush_during_recovery: str
    flush_verify_memtable_count: str
    db_host_id: str
    error_if_exists: str
    wal_recovery_mode: str
    enable_thread_tracking: str
    is_fd_close_on_exec: str
    enforce_single_del_contracts: str
    create_missing_column_families: str
    create_if_missing: str
    use_fsync: str
    wal_filter: str
    allow_2pc: str
    use_direct_io_for_flush_and_compaction: str
    manual_wal_flush: str
    enable_write_thread_adaptive_yield: str
    use_direct_reads: str
    allow_mmap_writes: str
    allow_fallocate: str
    two_write_queues: str
    allow_mmap_reads: str
    unordered_write: str
    advise_random_on_open: str

class CFOptions(BaseModel):
    memtable_max_range_deletions: int
    block_protection_bytes_per_key: int
    memtable_protection_bytes_per_key: int
    sample_for_compression: int
    blob_file_starting_level: int
    blob_compaction_readahead_size: int
    blob_garbage_collection_force_threshold: float
    enable_blob_garbage_collection: str
    min_blob_size: int
    last_level_temperature: str
    enable_blob_files: str
    target_file_size_base: int
    max_sequential_skip_in_iterations: int
    prepopulate_blob_cache: str
    compaction_options_fifo: str
    max_bytes_for_level_multiplier: float
    max_bytes_for_level_multiplier_additional: str
    max_bytes_for_level_base: int
    experimental_mempurge_threshold: float
    write_buffer_size: int
    bottommost_compression: str
    prefix_extractor: str
    blob_file_size: int
    memtable_huge_page_size: int
    bottommost_file_compaction_delay: int
    max_successive_merges: int
    compression_opts: str
    arena_block_size: int
    memtable_whole_key_filtering: str
    target_file_size_multiplier: int
    max_write_buffer_number: int
    blob_compression_type: str
    compression: str
    level0_stop_writes_trigger: int
    level0_slowdown_writes_trigger: int
    level0_file_num_compaction_trigger: int
    ignore_max_compaction_bytes_for_input: str
    max_compaction_bytes: int
    compaction_options_universal: str
    memtable_prefix_bloom_size_ratio: float
    hard_pending_compaction_bytes_limit: int
    bottommost_compression_opts: str
    blob_garbage_collection_age_cutoff: float
    ttl: int
    soft_pending_compaction_bytes_limit: int
    inplace_update_num_locks: int
    paranoid_file_checks: str
    check_flush_compaction_key_order: str
    periodic_compaction_seconds: int
    disable_auto_compactions: str
    report_bg_io_stats: str
    compaction_pri: str
    compaction_style: str
    merge_operator: str
    table_factory: str
    memtable_factory: str
    comparator: str
    compaction_filter_factory: str
    num_levels: int
    min_write_buffer_number_to_merge: int
    bloom_locality: int
    max_write_buffer_size_to_maintain: int
    sst_partitioner_factory: str
    preserve_internal_time_seconds: int
    preclude_last_level_data_seconds: int
    max_write_buffer_number_to_maintain: int
    default_temperature: str
    optimize_filters_for_hits: str
    level_compaction_dynamic_file_size: str
    memtable_insert_with_hint_prefix_extractor: str
    level_compaction_dynamic_level_bytes: str
    inplace_update_support: str
    persist_user_defined_timestamps: str
    compaction_filter: str
    force_consistency_checks: str

  
class TableOptions(BaseModel):
    num_file_reads_for_auto_readahead: int
    initial_auto_readahead_size: int
    metadata_cache_options: str
    enable_index_compression: str
    pin_top_level_index_and_filter: str
    read_amp_bytes_per_bit: int
    verify_compression: str
    prepopulate_block_cache: str
    format_version: int
    partition_filters: str
    metadata_block_size: int
    max_auto_readahead_size: int
    index_block_restart_interval: int
    block_size_deviation: int
    block_size: int
    detect_filter_construct_corruption: str
    no_block_cache: str
    checksum: str
    filter_policy: str
    data_block_hash_table_util_ratio: float
    block_restart_interval: int
    index_type: str
    pin_l0_filter_and_index_blocks_in_cache: str
    data_block_index_type: str
    cache_index_and_filter_blocks_with_high_priority: str
    whole_key_filtering: str
    index_shortening: str
    cache_index_and_filter_blocks: str
    block_align: str
    optimize_filters_for_memory: str
    flush_block_policy_factory: str


@make_field_optional
class RocksDBOptions(BaseModel):
    db_bench_options: DBBenchOptions
    version: Version
    db_options: DBOptions
    cf_options: CFOptions
    table_options: TableOptions

