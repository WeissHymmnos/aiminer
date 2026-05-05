#!/bin/bash
# Consolidated AIMiner status check
# Usage: bash scripts/check_status.sh [log_path]
# If log_path omitted, uses the latest hermes_*.log

cd /home/wh/Documents/aiminer

main_pid=$(pgrep -f 'python.*manager\.py' | head -1)
if [ -z "$main_pid" ]; then
    echo "NOT_RUNNING"
    python scripts/hermes_auto_runner.py status 2>&1
    exit 0
fi

# Process info
ps -o pid,%cpu,%mem,rss,etime -p $main_pid --no-headers 2>/dev/null

# Total resource usage across all children
pstree -p $main_pid 2>/dev/null | grep -oP '\d+' | sort -u | while read p; do
    ps -o rss= -p $p 2>/dev/null
done | awk '{s+=$1} END{print NR, "procs,", s/1024, "MB"}'

# Iteration progress
log="${1:-$(ls -t logs/hermes_*.log 2>/dev/null | head -1)}"
if [ -n "$log" ] && [ -f "$log" ]; then
    echo "---ITER---"
    grep -oP 'iteration \d+' "$log" | sort -t' ' -k2 -n | uniq -c | sort -rn
    echo "---ERR---"
    grep -ciE 'Request timed out|error|traceback|warning|failed' "$log" 2>/dev/null || echo "0"

    # Auto-append errors to daily error log
    errlog="results/error_log_$(date +%Y%m%d).txt"
    if [ -f "$log" ]; then
        new_errors=$(grep -iE 'error|traceback|warning|failed|timeout' "$log" | grep -v 'INFO')
        if [ -n "$new_errors" ]; then
            existing_count=0
            if [ -f "$errlog" ]; then
                existing_count=$(wc -l < "$errlog")
            fi
            echo "$new_errors" | while read line; do
                grep -qF "$line" "$errlog" 2>/dev/null || echo "$line" >> "$errlog"
            done
            new_count=$(wc -l < "$errlog")
            echo "ERR_LOG: $errlog ($new_count lines, was $existing_count)"
        fi
    fi
fi
