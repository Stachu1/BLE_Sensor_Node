#!/usr/bin/env bash
# One-command driver for the C23 rev B openEMS sims (laptop, Git Bash).
#
#   ./sim.sh export              export BSN-C23.kicad_pcb -> build/board.json and build/preview.png
#   ./sim.sh push                copy the scripts and build/board.json to the server
#   ./sim.sh run cases/x.json    push, then run a case list on the server in the background (runner.py)
#   ./sim.sh opt cases/opt.json  push, then start an optimizer run in the background (optimize.py)
#   ./sim.sh queue cases/x.json [parallel] [threads]   push, then add a case list to the server queue (queue.sh)
#   ./sim.sh qstatus             queue log, waiting jobs and running sims
#   ./sim.sh status              running sims and the tail of the logs
#   ./sim.sh pull                copy results (no field data) to results/, rebuild results/REPORT.md and the
#                                design records results/designs/<run>/ + results/DESIGNS.md (archive.py)
#
# Server: DevelopmentServer (~/.ssh/config), work dir ~/openems_compute/c23b, openEMS venv /opt/openEMS/venv.
set -euo pipefail
cd "$(dirname "$0")"
SSHCFG=/c/Users/SBA.OJ/.ssh/config
HOST=DevelopmentServer
RDIR=openems_compute/c23b
PY=/opt/openEMS/venv/bin/python
KPY="/c/Program Files/KiCad/10.0/bin/python.exe"
ssh_() { ssh -o BatchMode=yes -F "$SSHCFG" "$HOST" "$@"; }
scp_() { scp -q -F "$SSHCFG" "$@"; }

push() {
	ssh_ "mkdir -p $RDIR/build $RDIR/runs $RDIR/cases $RDIR/opt $RDIR/queue/done"
	scp_ antenna.py sim_board.py sim_ports.py runner.py optimize.py tune2d.py check_efficiency.py farfield.py simple_ifa.py poynting_check.py match_ideal.py queue.sh "$HOST:$RDIR/"
	scp_ build/board.json "$HOST:$RDIR/build/"
	for d in build/*/; do
		[ -f "$d/board.json" ] || continue
		ssh_ "mkdir -p $RDIR/$d"
		scp_ "$d/board.json" "$HOST:$RDIR/$d"
	done
}

case "${1:-}" in
export)
	"$KPY" export_board.py
	python preview.py
	;;
push)
	push
	;;
run)
	push
	scp_ "$2" "$HOST:$RDIR/cases/"
	n=$(basename "$2" .json)
	ssh_ "cd $RDIR && (nohup $PY -u runner.py cases/$n.json ${3:-2} ${4:-10} > cases/$n.log 2>&1 < /dev/null &)"
	echo "started $n, log: $RDIR/cases/$n.log"
	;;
opt)
	push
	scp_ "$2" "$HOST:$RDIR/cases/"
	n=$(basename "$2" .json)
	ssh_ "cd $RDIR && (nohup $PY -u ${3:-optimize.py} cases/$n.json > opt/$n.log 2>&1 < /dev/null &)"
	echo "started optimizer $n, log: $RDIR/opt/$n.log"
	;;
queue)
	push
	n=$(basename "$2" .json)
	seq=$(date +%Y%m%d%H%M%S)
	scp_ "$2" "$HOST:$RDIR/queue/${seq}_$n.p${3:-6}t${4:-3}.json"
	ssh_ "cd $RDIR && mkdir -p queue/done && (pgrep -f '^bash queue.sh' > /dev/null || (nohup bash queue.sh >> queue/queue.log 2>&1 < /dev/null &))"
	echo "queued $n"
	;;
qstatus)
	ssh_ "cd $RDIR && tail -n 6 queue/queue.log; ls queue/*.json 2>/dev/null; ps -eo etime,args | grep '[s]im_board.py' | sed 's|/home/oj/openems_compute/c23b/||g'"
	;;
status)
	ssh_ "cd $RDIR && ps -eo etime,args | grep '[s]im_board.py' | sed 's|/home/oj/openems_compute/c23b/||g'; tail -n 3 opt/*.log cases/*.log 2>/dev/null"
	;;
pull)
	mkdir -p results
	ssh_ "cd $RDIR && tar czf - runs/index.jsonl runs/*/result.json runs/*/S11.csv runs/*/S*P.s*p runs/*/pattern.npz opt cases 2>/dev/null" | tar xzf - -C results
	python report.py
	python archive.py
	;;
*)
	sed -n '2,12p' "$0"
	;;
esac
