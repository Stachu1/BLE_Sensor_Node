#!/usr/bin/env bash
# Server-side job queue for the antenna sims: keeps the server busy without gaps between batches.
# Start once on the server (nohup bash queue.sh >> queue/queue.log 2>&1 &). ./sim.sh queue starts it if needed.
#
# A job is queue/<seq>_<name>.p<parallel>t<threads>.json (a runner.py case list). Jobs start in name order
# whenever the threads of the running jobs plus the new job (parallel x threads) fit in BUDGET. A job copies
# itself to cases/<name>.json, runs runner.py (log cases/<name>.log) and moves to queue/done/ when finished.
# A job bigger than the budget starts alone. Stop the queue (running jobs continue) by creating queue/STOP.
cd "$(dirname "$0")"
PY=/opt/openEMS/venv/bin/python
BUDGET=${BUDGET:-20}
mkdir -p queue/done queue/running cases
declare -A PIDS NEED
while [ ! -e queue/STOP ]; do
	used=0
	for j in "${!PIDS[@]}"; do
		if kill -0 "${PIDS[$j]}" 2>/dev/null; then
			used=$((used + NEED[$j]))
		else
			echo "$(date '+%F %T') done  $j"
			mv "queue/running/$j.json" queue/done/ 2>/dev/null
			unset "PIDS[$j]" "NEED[$j]"
		fi
	done
	job=$(ls queue/*.json 2>/dev/null | sort | head -1)
	if [ -n "$job" ]; then
		base=$(basename "$job" .json)
		spec=${base##*.}
		name=${base%.*}
		name=${name#*_}
		par=$(echo "$spec" | sed -n 's/^p\([0-9]*\)t[0-9]*$/\1/p')
		thr=$(echo "$spec" | sed -n 's/^p[0-9]*t\([0-9]*\)$/\1/p')
		par=${par:-4}
		thr=${thr:-5}
		need=$((par * thr))
		if [ $((used + need)) -le "$BUDGET" ] || [ "$used" -eq 0 ]; then
			cp "$job" "cases/$name.json"
			mv "$job" "queue/running/$base.json"
			$PY -u runner.py "cases/$name.json" "$par" "$thr" > "cases/$name.log" 2>&1 &
			PIDS[$base]=$!
			NEED[$base]=$need
			echo "$(date '+%F %T') start $name parallel $par threads $thr (threads in use before: $used)"
			continue
		fi
	fi
	sleep 20
done
echo "$(date '+%F %T') queue stopped (running jobs continue)"
