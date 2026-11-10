#!/usr/bin/env bash
# Reset the box between rounds.
#   soft (default): kill chor's processes, wipe its work dir, re-plant canaries.
#   hard (--hard):  delete and recreate the whole VM (OrbStack has no snapshots).
set -uo pipefail
VM="${CHOR_POLICE_VM:-chorbox}"

if [ "${1:-}" = "--hard" ]; then
  echo "==> hard reset: deleting and recreating '$VM'"
  orbctl delete "$VM" 2>/dev/null || true
  exec "$(dirname "$0")/setup.sh"
fi

echo "==> soft reset of '$VM'"
orb -m "$VM" bash -lc '
  sudo pkill -u chor 2>/dev/null || true          # clear sleeper leftovers
  sudo rm -rf /home/chor/work && sudo mkdir -p /home/chor/work
  echo "print(\"hello from chor\")" | sudo tee /home/chor/work/task.py >/dev/null
  sudo chown -R chor:chor /home/chor/work
'
echo "   done (canaries are re-planted per round by the referee)"
