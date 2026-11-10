#!/usr/bin/env bash
# Create the throwaway, ISOLATED OrbStack Linux VM for Chor Police, install
# bubblewrap, add a non-sudo `chor` user, plant the box layout, and run the
# isolation check.
#
# Verified on OrbStack 2.2.5 (arm64). `--isolated` removes the /mnt/mac mount
# and blocks `mac` commands; `--isolate-network` blocks the Mac host + other
# machines. NOTE: all OrbStack machines share one kernel -- this is a soft
# boundary, fine for sandbox-escape play (grabbing canaries), NOT for code that
# exploits the kernel. For a hard boundary use Lima (vmType vz) or UTM.
set -uo pipefail

VM="${CHOR_POLICE_VM:-chorbox}"

echo "==> creating isolated VM '$VM'"
if ! orbctl list 2>/dev/null | awk '{print $1}' | grep -qx "$VM"; then
  orbctl create --isolated --isolate-network ubuntu "$VM"
else
  echo "   (exists, reusing)"
fi

echo "==> installing bubblewrap"
orb -m "$VM" bash -lc 'sudo apt-get update -qq && sudo apt-get install -y -qq bubblewrap'

echo "==> adding non-sudo user 'chor' + planting box layout"
orb -m "$VM" bash -lc '
  sudo useradd -m chor 2>/dev/null || true          # chor is not in sudo group -> no sudo
  sudo mkdir -p /home/chor/work /etc/app
  echo "print(\"hello from chor\")" | sudo tee /home/chor/work/task.py >/dev/null
  echo "token=PLANTED_PER_ROUND"   | sudo tee /etc/app/secret.conf >/dev/null
  echo "PLANTED_PER_ROUND"         | sudo tee /home/host_flag.txt >/dev/null
  sudo chown -R chor:chor /home/chor
  sudo chmod 700 /home/chor
'

echo ""
echo "==> ISOLATION CHECK (all must FAIL for a safe box)"
pass=0
# capture to a var (no pipe) so pipefail + non-zero exits don't skew the result;
# each check looks for the BAD signal and fails only on that.
run() { orb -m "$VM" -u chor bash -lc "$1" 2>&1; }

o=$(run 'test -e /mnt/mac && echo PRESENT || echo ABSENT')
case "$o" in *ABSENT*) echo "   [1] ok: no /mnt/mac mount";;
             *) echo "   [1] FAIL: /mnt/mac present"; pass=1;; esac

o=$(run 'mac uname -s')
case "$o" in *Darwin*) echo "   [2] FAIL: mac command works"; pass=1;;
             *) echo "   [2] ok: mac command blocked";; esac

o=$(run 'ping -c1 -W2 host.orb.internal')
case "$o" in *Darwin*|*"bytes from"*) echo "   [3] FAIL: host reachable"; pass=1;;
             *) echo "   [3] ok: host not reachable";; esac

echo ""
if [ "$pass" -eq 0 ]; then
  echo "==> ISOLATION OK — safe to play:  PYTHONPATH=. python3 tussle.py --mode vm"
else
  echo "==> ISOLATION INCOMPLETE — recreate with --isolated --isolate-network, or use --mode fake."
fi
echo ""
echo "reminder: your other machines (ubuntu, tiny, qemuiso) share this kernel — keep no secrets there."
