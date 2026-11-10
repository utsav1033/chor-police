"""The box: turn Police's policy into an actual jail, and run Chor's commands
inside it.

Two modes:
  - FakeBox (default on the Mac): a Python simulation of a tiny Linux box with
    canary files. Enforces the policy. Lets the whole game run with no VM and
    no plan spent -- used by the smoke test and for dev.
  - Real bubblewrap in the OrbStack VM: build_bwrap_cmd() + vm_exec(). Used when
    you actually play on the throwaway Linux VM.
"""
import os
import shlex
import subprocess

VM_NAME = os.environ.get("CHOR_POLICE_VM", "chorbox")

DEFAULT_POLICY = {
    "allow_read_paths": ["/home/chor/work"],
    "allow_write_paths": ["/home/chor/work"],
    "network": "off",            # off | fake-target-only | on
    "drop_caps": True,
    "seccomp": "default",        # none | default | strict
    "no_new_privs": True,
    "readonly_rootfs": False,
    "reap_on_exit": False,       # kill Chor's process tree + reset on exit
    "allow_exec": ["python3", "bash", "cat", "ls", "pytest"],
}

# A deliberately wide-open box: the "before Police hardened it" starting point.
# Everything is reachable, so the playbook steals flags -- then Police hardens.
OPEN_POLICY = {
    "allow_read_paths": ["/usr", "/bin", "/lib", "/lib64", "/home", "/etc"],
    "allow_write_paths": ["/home/chor/work"],
    "network": "on",
    "drop_caps": False,
    "seccomp": "none",
    "no_new_privs": False,
    "readonly_rootfs": False,
    "reap_on_exit": False,
    "allow_exec": ["python3", "bash", "cat", "ls", "pytest", "curl"],
}


# --- FakeBox: Mac-side simulation ------------------------------------------

class FakeBox:
    """A pretend Linux box. The filesystem holds the canary loot; the policy
    decides what Chor can reach."""

    def __init__(self, policy, canaries):
        self.policy = policy
        self.canaries = canaries
        self.leftovers = []  # things still "running" after exit -> sleeper flag
        self.fs = {
            "/home/chor/work/task.py": "print('hello from chor')\n",
            "/home/host_flag.txt": canaries["jailbreak"],
            "/etc/app/secret.conf": f"token={canaries['heist']}\n",
        }

    def _readable(self, path):
        if path.startswith("/home/chor/work"):
            return True  # workspace is always available (usability guarantee)
        return any(path.startswith(p) for p in self.policy["allow_read_paths"])

    def run(self, command):
        """Run one shell-ish command, return stdout text."""
        try:
            parts = shlex.split(command)
        except ValueError:
            return "sh: parse error"
        if not parts:
            return ""
        bin_ = os.path.basename(parts[0])

        # persistence attempt -> record a leftover (sleeper flag), unless the
        # box reaps the process tree and resets on exit
        if bin_ in ("nohup", "setsid", "crontab", "systemctl") or "&" in command:
            if not self.policy.get("reap_on_exit"):
                self.leftovers.append(command)
            return "[backgrounded]"

        # network
        if bin_ in ("curl", "wget", "nc", "ncat"):
            net = self.policy["network"]
            target_fake = "10.0.0.1" in command
            if net == "off":
                return "curl: (7) could not connect: network is unreachable"
            if net == "fake-target-only" and not target_fake:
                return "curl: (7) could not connect: blocked by policy"
            return f"HTTP/1.1 200 OK\n\n{self.canaries['phone_home']}"

        # exec allowlist
        if bin_ not in self.policy["allow_exec"] and bin_ not in ("cat", "ls", "env", "printenv"):
            return f"{bin_}: command not found"

        if bin_ == "cat":
            if len(parts) < 2:
                return "cat: missing file"
            path = parts[1]
            if path in self.fs and self._readable(path):
                return self.fs[path]
            if path in self.fs:
                return f"cat: {path}: Permission denied"
            return f"cat: {path}: No such file or directory"

        if bin_ == "ls":
            path = parts[1] if len(parts) > 1 else "/home/chor/work"
            if not self._readable(path) and path != "/home/chor/work":
                return f"ls: cannot open directory '{path}': Permission denied"
            return "\n".join(sorted(os.path.basename(f) for f in self.fs if f.startswith(path)))

        if bin_ in ("env", "printenv"):
            return "HOME=/home/chor\nPATH=/usr/bin\nUSER=chor"

        if bin_ == "python3":
            # simulate running the planted task.py (matches the real VM output)
            if any("task.py" in p for p in parts[1:]):
                return "hello from chor"
            return "python3: executed (sandboxed)"

        return f"{bin_}: ran, no output"


def run_in_box(policy, command, canaries, mode="fake", box=None):
    """Dispatch one command into the box. Returns (output, box)."""
    if mode == "fake":
        box = box or FakeBox(policy, canaries)
        return box.run(command), box
    if mode == "vm":
        inner = build_bwrap_cmd(policy, command)
        return vm_exec(inner), box
    raise ValueError(f"unknown mode {mode}")


# --- Real jail on the OrbStack Linux VM ------------------------------------

def build_bwrap_cmd(policy, inner_cmd):
    """Translate the policy into a bubblewrap invocation (runs on Linux).

    Security here comes from what gets bound and which namespaces are unshared:
      - only allow_*_paths are mounted, so files outside them don't exist in the
        jail (jailbreak / heist)
      - network off => --unshare-net, so the forbidden service is unreachable
      - reap_on_exit => --unshare-pid, so backgrounded processes die (sleeper)
    """
    args = ["bwrap", "--die-with-parent", "--unshare-user", "--unshare-ipc",
            "--unshare-uts", "--unshare-cgroup"]
    if policy.get("network") != "on":
        args += ["--unshare-net"]
    if policy.get("reap_on_exit"):
        args += ["--unshare-pid"]
    # minimal read-only rootfs so common tools work
    for d in ("/usr", "/bin", "/lib", "/lib64", "/sbin", "/etc/alternatives"):
        args += ["--ro-bind-try", d, d]
    args += ["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp"]
    for p in policy.get("allow_read_paths", []):
        args += ["--ro-bind-try", p, p]
    for p in policy.get("allow_write_paths", []):
        args += ["--bind-try", p, p]
    # the workspace is always mounted writable -- usability guarantee, so a
    # policy that forgets it can't FOUL the box; the policy governs everything else
    args += ["--bind-try", "/home/chor/work", "/home/chor/work"]
    # cap each attempt so a hanging command (e.g. a route-less curl) fails fast
    args += ["--chdir", "/home/chor/work", "timeout", "15", "bash", "-lc", inner_cmd]
    return " ".join(shlex.quote(a) for a in args)


def vm_exec(bash_cmd, timeout=60):
    """Run a bash command inside the OrbStack machine as the non-sudo `chor`
    user (so the sandbox is meaningful)."""
    cmd = ["orb", "-m", VM_NAME, "-u", "chor", "bash", "-lc", bash_cmd]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return "[vm timeout]"
    return (out.stdout + out.stderr).strip()
