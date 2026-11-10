"""VM-mode round helpers: plant this round's canaries into the OrbStack VM,
run the 'forbidden' network service, and detect leftovers (sleeper flag).

The forbidden target is a tiny HTTP service on the VM's loopback. A box with
network off (--unshare-net) can't reach it; a box with network on can -- so the
phone_home flag is gated by the policy, exactly like the file flags are gated by
which paths get bound.
"""
import shlex
import subprocess
import time
import types

from cp.box import VM_NAME

NET_PORT = 8099
NET_TARGET = f"http://127.0.0.1:{NET_PORT}/"


def _vm(bash, user=None, timeout=30, bg=False):
    cmd = ["orb", "-m", VM_NAME]
    if user:
        cmd += ["-u", user]
    cmd += ["bash", "-lc", bash]
    if bg:
        return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def prep_round(canaries):
    """Reset box state and plant this round's loot."""
    _vm(f"sudo pkill -u chor 2>/dev/null; sudo pkill -f chorcanary 2>/dev/null; true")
    jb = shlex.quote(canaries["jailbreak"])
    secret = shlex.quote("token=" + canaries["heist"])
    _vm(
        f"echo {jb} | sudo tee /home/host_flag.txt >/dev/null; "
        f"echo {secret} | sudo tee /etc/app/secret.conf >/dev/null; "
        f"printf 'print(\"hello from chor\")\\n' | sudo tee /home/chor/work/task.py >/dev/null; "
        # loot is world-readable on purpose: the SANDBOX (which paths Police binds)
        # must be the only thing gating it, not Unix file permissions
        f"sudo chown -R chor:chor /home/chor/work; sudo chmod 644 /home/host_flag.txt /etc/app/secret.conf"
    )
    server = (
        "import http.server,socketserver\n"
        "socketserver.TCPServer.allow_reuse_address=True\n"  # survive fast box restarts
        f"C={canaries['phone_home']!r}\n"
        "class H(http.server.BaseHTTPRequestHandler):\n"
        " def do_GET(self):\n"
        "  self.send_response(200);self.end_headers();self.wfile.write(C.encode())\n"
        " def log_message(self,*a):pass\n"
        f"socketserver.TCPServer(('127.0.0.1',{NET_PORT}),H).serve_forever()\n"
    )
    _vm(f"nohup python3 -c {shlex.quote(server)} chorcanary >/tmp/chorcanary.log 2>&1 &", bg=True)
    time.sleep(1)


def collect_leftovers():
    """Any chor-owned process still running after the round = sleeper."""
    time.sleep(1)
    out = _vm("pgrep -u chor -a 2>/dev/null || true").stdout.strip()
    lines = [l for l in out.splitlines() if l and "pgrep" not in l]
    return types.SimpleNamespace(leftovers=lines)
