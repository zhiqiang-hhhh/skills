---
name: clickhouse-replica-io-diagnostics
description: Diagnose ClickHouse replicated-cluster performance by comparing direct INSERT traffic, NewPart and DownloadPart creation, merge activity, replication queues, load average, OS iowait, disk placement, filesystem cache, and Linux dirty-page throttling. Use when replicas show unequal load, high wa, high load average, merge pressure, replication lag, excessive small parts, suspected EBS differences, or a change in write-routing behavior.
---

# ClickHouse Replica I/O Diagnostics

## Purpose

Determine why ClickHouse replicas have different CPU, I/O wait, load, merge, or replication pressure. Keep observations, direct causes, and root causes separate.

Run only read-only SQL and OS inspection commands unless the user explicitly requests a change.

## Workflow

1. Confirm cluster topology and replica macros.
2. Compare direct INSERT traffic over both a short window and a longer window.
3. Compare `NewPart`, `DownloadPart`, and `MergeParts`.
4. Measure average and percentile NewPart sizes. Treat a high rate of KiB-sized parts as a primary write-amplification signal.
5. Compare active merges and replication queues.
6. Compare `LoadAverage*` and `OSIOWaitTimeNormalized`.
7. Determine whether work uses the local disk or object storage before discussing cache or EBS.
8. When iowait is high, inspect Linux D-state threads, dirty pages, filesystem journal waits, and block-device statistics.
9. Re-sample after routing or configuration changes. Do not infer a trend from one instantaneous value.

Use `scripts/collect_replica_io_report.sh` for the standard ClickHouse report.

## Metric Interpretation

### Write path

- `system.query_log`, `query_kind = 'Insert'`: identifies the node receiving a client INSERT.
- `system.part_log`, `NewPart`: identifies locally created parts from direct writes.
- `system.part_log`, `DownloadPart`: identifies parts fetched from another replica.
- `system.part_log`, `MergeParts`: identifies completed local merges.

Do not call a node "the writer" based only on final data volume. Use INSERT and `NewPart` distribution.

### Part size

Use `size_in_bytes` for on-disk part size and `rows` for rows per part. Report at least:

- count
- average
- p50
- p90
- p99
- rows per part
- percentage below 4 KiB, 16 KiB, 64 KiB, and 1 MiB when small parts are suspected

Average NewPart sizes of only a few KiB indicate pathological small-batch writes even when total throughput is high.

### Merge pressure

Compare:

- completed merge count and output bytes
- active merge count
- total source bytes and source part count
- merge duration and progress
- replication merge queue

More merge count does not always mean more pressure. Also compare bytes, source parts, duration, and current backlog.

### Replication pressure

Use `system.replicas`:

- `queue_size`
- `inserts_in_queue`
- `merges_in_queue`
- `absolute_delay`

An evenly split client write rate can still produce uneven replica pressure because each replica independently fetches and merges parts and may have historical backlog.

### I/O wait and load

`OSIOWaitTimeNormalized * 100` is comparable to recent OS `%iowait`.

Do not describe `%wa` as CPUs actively executing I/O waits. It is CPU time that was idle while the kernel had outstanding block-I/O waits. On a 32-vCPU host, `wa = 40%` is approximately 12.8 CPU-seconds per one-second interval classified as iowait. Waiting threads, often in D state, are not running on those CPUs.

A host can have lower `%wa` while its disk is equally busy if runnable CPU work fills otherwise idle CPU time. Therefore:

- `%util = 100%` does not imply high `%wa`.
- Lower `%wa` does not prove lower disk pressure.
- Load average includes runnable tasks and uninterruptible D-state tasks.
- High load can persist or spike while current `%wa` is lower.

## Distinguish Cache Types

`FilesystemCacheBytes` and `system.filesystem_cache_settings` describe ClickHouse remote-filesystem/object-storage cache. They are not Linux page cache metrics.

Before attributing local Merge performance to this cache:

1. Check `system.part_log.disk_name`.
2. Check active parts in `system.parts`.
3. Confirm merges actually occur on `s3_disk` or the cached disk.

For local MergeTree data on `default`, inspect Linux page cache, dirty pages, and the local block device instead.

## Linux Validation

Use these commands on each replica:

```bash
iostat -x 1 -d <device>
pidstat -d -p "$(pidof clickhouse-server)" 1
ps -eLo state,pid,tid,wchan:32,comm | awk '$1=="D"'
grep -E 'Dirty|Writeback|MemAvailable' /proc/meminfo
sysctl vm.dirty_ratio vm.dirty_background_ratio \
  vm.dirty_bytes vm.dirty_background_bytes \
  vm.dirty_writeback_centisecs vm.dirty_expire_centisecs
grep -E 'nr_dirty|nr_writeback|nr_dirtied|nr_written|dirty_threshold|throttle' /proc/vmstat
dmesg | grep -iE 'nvme|ext4|xfs|blk|error|reset|timeout'
```

Interpret important waits:

- `balance_dirty_pages`: writer throttled because dirty pages approach the kernel limit.
- `jbd2_log_do_checkpoint`: EXT4 journal checkpoint pressure.
- many `MergeMutate` threads in D state: merge writes are blocked by storage/writeback.

Dirty-page throttling is a direct cause of elevated load and iowait. It is usually not the root cause. Trace it back to write rate, part count, replication fetches, merge amplification, and storage capability.

## EBS Diagnosis

Equal provisioned volume settings do not prove equal effective performance. Check:

- identical instance type and EBS-optimized limits
- volume type, size, IOPS, and throughput
- `VolumeIOPSExceededCheck`
- `VolumeThroughputExceededCheck`
- `VolumeStalledIOCheck`
- `InstanceEBSIOPSExceededCheck`
- `InstanceEBSThroughputExceededCheck`
- volume latency and queue length
- burst balance metrics when applicable

Do not conclude one EBS volume is slower merely because its host has higher `%wa`. Under comparable workload, look for persistently higher latency, lower achieved throughput/IOPS, exceeded checks, or degraded volume status.

## Required Conclusion Shape

Report:

1. Current write routing: one-sided, balanced, or recently changed.
2. Part health: NewPart rate and size.
3. Replication direction and backlog.
4. Merge pressure on each replica.
5. Current iowait and load, with correct `%wa` semantics.
6. Storage path involved: local disk or object storage.
7. Direct cause, root cause, and remaining uncertainty.
8. The smallest next check that can disprove the conclusion.

State explicitly when a prior hypothesis is invalidated by new evidence.
