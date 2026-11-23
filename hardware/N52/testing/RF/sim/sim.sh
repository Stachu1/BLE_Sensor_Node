#!/usr/bin/env bash
# One-command driver for the BSN-N52 (ex AirTag) antenna sims (laptop, Git Bash, run from anywhere).
#
#   ./sim.sh export [rev]        export ../../../BSN-N52.kicad_pcb -> build/<rev>/board.json (KiCad python), never in place
#   ./sim.sh push                copy the scripts and every build/*/board.json to the server
#   ./sim.sh run cases/x.json [par] [thr]    push, then run a case list on the server in the background (runner.py)
#   ./sim.sh tune cases/x.json [par] [thr]   push, then start tune.py on a case list in the background
#   ./sim.sh queue cases/x.json [par] [thr]  push, then add a case list to the server queue (queue.sh)
#   ./sim.sh qstatus             queue log, waiting jobs and running sims
#   ./sim.sh qrestart            copy queue.sh and restart the queue (push never copies queue.sh)
#   ./sim.sh status              running sims and the tail of the logs
#   ./sim.sh bench [thr]         dipole reference check of the far-field code (expect 100 %, 2.15 dBi)
#   ./sim.sh pull                copy results (no field data) to results/ and rebuild results/DESIGNS.md (report.py)
#
# Server: DevelopmentServer (~/.ssh/config), work dir ~/openems_compute/airtag, openEMS venv /opt/openEMS/venv.
set -euo pipefail
cd "$(dirname "$0")"
SSHCFG=/c/Users/SBA.OJ/.ssh/config
HOST=DevelopmentServer
RDIR=openems_compute/airtag
PY=/opt/openEMS/venv/bin/python
KPY="/c/Program Files/KiCad/10.0/bin/python.exe"
ssh_() { ssh -o BatchMode=yes -F "$SSHCFG" "$HOST" "$@"; }
scp_() { scp -q -F "$SSHCFG" "$@"; }

push() {
	ssh_ "mkdir -p $RDIR/build $RDIR/runs $RDIR/cases $RDIR/opt $RDIR/queue/done"
	scp_ antenna.py sim_board.py runner.py tune.py farfield.py check_efficiency.py match_ideal.py synth_board.py feedport.py match_tee.py combine_multi.py "$HOST:$RDIR/"
	ssh_ "test -f $RDIR/queue.sh" || scp_ queue.sh "$HOST:$RDIR/"
	for d in build/*/; do
		[ -f "$d/board.json" ] || continue
		ssh_ "mkdir -p $RDIR/$d"
		scp_ "$d/board.json" "$HOST:$RDIR/$d"
	done
}

case "${1:-}" in
export)
	rev=${2:?usage: ./sim.sh export <rev>}
	[ -e "build/$rev/board.json" ] && { echo "build/$rev exists, use a new rev name (the result cache keys on the path)"; exit 1; }
	"$KPY" export_board.py ../../../BSN-N52.kicad_pcb "build/$rev"
	;;
push)
	push
	;;
run|tune)
	push
	scp_ "$2" "$HOST:$RDIR/cases/"
	n=$(basename "$2" .json)
	if [ "$1" = run ]; then prog=runner.py; log=cases/$n.log; else prog=tune.py; log=opt/$n.log; fi
	ssh_ "cd $RDIR && (nohup $PY -u $prog cases/$n.json ${3:-4} ${4:-5} > $log 2>&1 < /dev/null &)"
	echo "started $prog $n, log: $RDIR/$log"
	;;
queue)
	push
	n=$(basename "$2" .json)
	seq=$(date +%Y%m%d%H%M%S)
	scp_ "$2" "$HOST:$RDIR/queue/${seq}_$n.p${3:-4}t${4:-5}.json"
	# a queue.sh of another project (BSN c23b) matched the bare pgrep (2026-11-15): only count one running in this folder
	ssh_ "cd $RDIR && (for p in \$(pgrep -f '^bash queue.sh'); do [ \"\$(readlink /proc/\$p/cwd)\" = \"\$PWD\" ] && exit 0; done; nohup bash queue.sh >> queue/queue.log 2>&1 < /dev/null &)"
	echo "queued $n"
	;;
qrestart)
	ssh_ "cd $RDIR && for p in \$(pgrep -f '^bash queue.sh'); do kill \$p; done"
	scp_ queue.sh "$HOST:$RDIR/"
	ssh_ "cd $RDIR && (nohup bash queue.sh >> queue/queue.log 2>&1 < /dev/null &)"
	echo "queue restarted"
	;;
qstatus)
	ssh_ "cd $RDIR && tail -n 6 queue/queue.log 2>/dev/null; ls queue/*.json 2>/dev/null; ps -eo etime,args | grep '[s]im_board.py' | sed 's|/home/oj/openems_compute/airtag/||g'"
	;;
status)
	ssh_ "cd $RDIR && ps -eo etime,args | grep '[s]im_board.py\|[c]heck_efficiency' | sed 's|/home/oj/openems_compute/airtag/||g'; tail -n 4 opt/*.log cases/*.log 2>/dev/null"
	;;
bench)
	push
	ssh_ "cd $RDIR && (nohup $PY -u check_efficiency.py bench/dipole ${2:-8} > cases/bench_dipole.log 2>&1 < /dev/null &)"
	echo "started dipole bench, log: $RDIR/cases/bench_dipole.log"
	;;
pull)
	mkdir -p results
	ssh_ "cd $RDIR && tar czf - runs/index.jsonl runs/*/case.json runs/*/result.json runs/*/S11.csv runs/*/pattern.npz runs/*/run.log opt cases 2>/dev/null" | tar xzf - -C results
	python report.py
	;;
*)
	sed -n '2,14p' "$0"
	;;
esac
