#!/usr/bin/env bash
set -euo pipefail

: "${CLICKHOUSE_HOST:?Set CLICKHOUSE_HOST}"
: "${CLICKHOUSE_USER:?Set CLICKHOUSE_USER}"
: "${CLICKHOUSE_PASSWORD:?Set CLICKHOUSE_PASSWORD}"
: "${CLICKHOUSE_CLUSTER:?Set CLICKHOUSE_CLUSTER}"

WINDOW_MINUTES="${WINDOW_MINUTES:-5}"

clickhouse client \
    --host "${CLICKHOUSE_HOST}" \
    --user "${CLICKHOUSE_USER}" \
    --password "${CLICKHOUSE_PASSWORD}" \
    --multiquery \
    --param_cluster "${CLICKHOUSE_CLUSTER}" \
    --param_window_minutes "${WINDOW_MINUTES}" \
    --query "
SELECT
    cluster,
    shard_num,
    replica_num,
    host_name,
    host_address,
    is_local
FROM system.clusters
WHERE cluster = {cluster:String}
ORDER BY shard_num, replica_num
FORMAT PrettyCompact;

SELECT
    hostName() AS host,
    count() AS insert_queries,
    sum(written_rows) AS written_rows,
    formatReadableSize(sum(written_bytes)) AS written_bytes
FROM clusterAllReplicas({cluster:String}, system.query_log)
WHERE event_time >= now() - toIntervalMinute({window_minutes:UInt32})
  AND type = 'QueryFinish'
  AND query_kind = 'Insert'
GROUP BY host
ORDER BY host
FORMAT PrettyCompact;

SELECT
    host,
    event_type,
    count() AS parts,
    sum(part_rows) AS total_rows,
    formatReadableSize(sum(part_size)) AS total_size,
    formatReadableSize(avg(part_size)) AS avg_part_size,
    formatReadableSize(quantileExact(0.5)(part_size)) AS p50_part_size,
    formatReadableSize(quantileExact(0.9)(part_size)) AS p90_part_size,
    formatReadableSize(quantileExact(0.99)(part_size)) AS p99_part_size,
    round(avg(part_rows), 2) AS avg_rows_per_part
FROM
(
    SELECT
        hostName() AS host,
        event_type,
        rows AS part_rows,
        size_in_bytes AS part_size
    FROM clusterAllReplicas({cluster:String}, system.part_log)
    WHERE event_time >= now() - toIntervalMinute({window_minutes:UInt32})
      AND event_type IN ('NewPart', 'DownloadPart', 'MergeParts')
      AND error = 0
)
GROUP BY host, event_type
ORDER BY host, event_type
FORMAT PrettyCompact;

SELECT
    hostName() AS host,
    count() AS active_merges,
    sum(num_parts) AS source_parts,
    formatReadableSize(sum(total_size_bytes_compressed)) AS source_size,
    round(avg(elapsed), 2) AS avg_elapsed_seconds,
    round(max(elapsed), 2) AS max_elapsed_seconds,
    countIf(progress < 0.01 AND elapsed > 300) AS slow_low_progress
FROM clusterAllReplicas({cluster:String}, system.merges)
GROUP BY host
ORDER BY host
FORMAT PrettyCompact;

SELECT
    hostName() AS host,
    sum(queue_size) AS queue_size,
    sum(inserts_in_queue) AS inserts_in_queue,
    sum(merges_in_queue) AS merges_in_queue,
    max(absolute_delay) AS max_delay_seconds
FROM clusterAllReplicas({cluster:String}, system.replicas)
GROUP BY host
ORDER BY host
FORMAT PrettyCompact;

SELECT
    hostName() AS host,
    metric,
    round(value, 4) AS value,
    if(
        metric = 'OSIOWaitTimeNormalized',
        concat(toString(round(value * 100, 2)), '%'),
        ''
    ) AS percent
FROM clusterAllReplicas({cluster:String}, system.asynchronous_metrics)
WHERE metric IN (
    'LoadAverage1',
    'LoadAverage5',
    'LoadAverage15',
    'OSIOWaitTimeNormalized'
)
ORDER BY host, metric
FORMAT PrettyCompact;

SELECT
    hostName() AS host,
    disk_name,
    countDistinct(database, table) AS tables,
    count() AS active_parts,
    formatReadableSize(sum(bytes_on_disk)) AS bytes_on_disk
FROM clusterAllReplicas({cluster:String}, system.parts)
WHERE active
GROUP BY host, disk_name
ORDER BY host, disk_name
FORMAT PrettyCompact;
"
