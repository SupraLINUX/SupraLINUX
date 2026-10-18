#!/usr/bin/env python3
import json
import os
import pwd
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPOSITORY = "SupraLINUX/SupraLINUX"
PR_NUMBER = 1
RUNNER_USER = "supralinux-orchestrator"
BOOTSTRAP_EVIDENCE = Path("/var/lib/supralinux/evidence/host-orchestrator-bootstrap")
WORK_ROOT = Path("/var/lib/supralinux/host-authoritative-control")
RESULT_ROOT = Path("/var/lib/supralinux/host-authoritative-control-results")
GOLDEN_IMAGE = Path("/var/lib/supralinux/images/ubuntu-26.04-authoritative.qcow2")
MAX_REQUEST_BYTES = 16_384
API_VERSION = "2026-03-10"

if os.geteuid() != 0:
    raise SystemExit("Authoritative host broker must run through sudo.")
if os.environ.get("SUDO_USER") != RUNNER_USER:
    raise SystemExit(f"Unexpected broker caller: {os.environ.get('SUDO_USER', 'unset')}")

raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
if not raw or len(raw) > MAX_REQUEST_BYTES:
    raise SystemExit(f"Invalid request size: {len(raw)}")
request = json.loads(raw)
allowed_keys = {
    "schema", "mode", "gate", "runner_group_id", "cancel_run_id",
    "source_commit", "control_run_id",
}
unknown = set(request) - allowed_keys
if unknown:
    raise SystemExit(f"Unknown authoritative request keys: {sorted(unknown)}")
if request.get("schema") != 1:
    raise SystemExit("Unsupported request schema.")
if request.get("mode") not in {"preflight", "execute"}:
    raise SystemExit("Unsupported control mode.")
if request.get("gate") != "plasma-package-build":
    raise SystemExit("Unsupported authoritative gate.")

source_commit = request.get("source_commit")
control_run_id = request.get("control_run_id")
runner_group_id = request.get("runner_group_id")
cancel_run_id = request.get("cancel_run_id")
if not isinstance(source_commit, str) or len(source_commit) != 40 or any(c not in "0123456789abcdef" for c in source_commit):
    raise SystemExit("Invalid source commit.")
if not isinstance(control_run_id, str) or not control_run_id.isdigit():
    raise SystemExit("Invalid control run id.")
if not isinstance(runner_group_id, int) or runner_group_id <= 0:
    raise SystemExit("Invalid runner group id.")
if cancel_run_id is not None and (not isinstance(cancel_run_id, int) or cancel_run_id <= 0):
    raise SystemExit("Invalid cancellation run id.")
if request["mode"] == "execute" and cancel_run_id is not None:
    raise SystemExit("execute mode refuses cancellation; stale-run cleanup belongs to preflight.")

for command in ("curl", "git", "gh", "jq", "python3"):
    if shutil.which(command) is None:
        raise SystemExit(f"Missing host command: {command}")

runner_pw = pwd.getpwnam(RUNNER_USER)
WORK_ROOT.mkdir(parents=True, exist_ok=True)
RESULT_ROOT.mkdir(parents=True, exist_ok=True)
result_dir = RESULT_ROOT / control_run_id
if result_dir.exists():
    raise SystemExit(f"Control result already exists: {result_dir}")
result_dir.mkdir(mode=0o700)
os.chown(result_dir, runner_pw.pw_uid, runner_pw.pw_gid)

def write_result(name: str, content: str) -> None:
    path = result_dir / name
    path.write_text(content)
    os.chmod(path, 0o600)
    os.chown(path, runner_pw.pw_uid, runner_pw.pw_gid)

def resolve_operator() -> pwd.struct_passwd:
    records = []
    if BOOTSTRAP_EVIDENCE.is_dir():
        for result in BOOTSTRAP_EVIDENCE.glob("*/result.txt"):
            try:
                fields = dict(
                    line.split("=", 1)
                    for line in result.read_text().splitlines()
                    if "=" in line
                )
                if fields.get("state") != "PASS" or fields.get("runner_user") != RUNNER_USER:
                    continue
                owner = pwd.getpwuid(result.stat().st_uid)
                if owner.pw_name in {"root", RUNNER_USER}:
                    continue
                records.append((result.stat().st_mtime_ns, owner, result))
            except (OSError, KeyError, ValueError):
                continue
    if not records:
        raise SystemExit("No certified bootstrap operator could be resolved.")
    records.sort(key=lambda item: item[0], reverse=True)
    newest_mtime = records[0][0]
    newest = [item for item in records if item[0] == newest_mtime]
    owners = {item[1].pw_name for item in newest}
    if len(owners) != 1:
        raise SystemExit("Ambiguous latest bootstrap operator.")
    return newest[0][1]

operator = resolve_operator()

def demote():
    os.initgroups(operator.pw_name, operator.pw_gid)
    os.setgid(operator.pw_gid)
    os.setuid(operator.pw_uid)

def run_as_operator(args, *, cwd=None, extra_env=None, check=True, capture_output=True):
    env = os.environ.copy()
    env.update({
        "HOME": operator.pw_dir,
        "USER": operator.pw_name,
        "LOGNAME": operator.pw_name,
    })
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        check=check,
        capture_output=capture_output,
        text=True,
        preexec_fn=demote,
    )

libvirt_group = pwd.getpwnam("libvirt-qemu").pw_gid
group_names = set(
    run_as_operator(["id", "-nG"]).stdout.split()
)
libvirt_group_name = __import__("grp").getgrgid(libvirt_group).gr_name
if libvirt_group_name not in group_names:
    raise SystemExit("Resolved operator lacks libvirt QEMU group.")
run_as_operator(["test", "-r", "/dev/kvm"])
run_as_operator(["test", "-w", "/dev/kvm"])
run_as_operator(["gh", "auth", "status", "--hostname", "github.com"])
token_result = run_as_operator(["gh", "auth", "token"])
token = token_result.stdout.strip()
if not token:
    raise SystemExit("Could not acquire host operator GitHub token.")

def api(method: str, path: str, body=None, allowed=(200, 201, 202, 204)):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": API_VERSION,
            **({"Content-Type": "application/json"} if data is not None else {}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            status = response.status
            payload = response.read()
    except urllib.error.HTTPError as exc:
        status = exc.code
        payload = exc.read()
    if status not in allowed:
        raise SystemExit(f"GitHub API {method} {path} failed with HTTP {status}.")
    if not payload:
        return None
    return json.loads(payload)

pr = api("GET", f"/repos/{REPOSITORY}/pulls/{PR_NUMBER}", allowed=(200,))
if not (
    pr.get("state") == "open"
    and pr.get("head", {}).get("sha") == source_commit
    and pr.get("head", {}).get("repo", {}).get("full_name") == REPOSITORY
):
    raise SystemExit("PR identity/head no longer matches the authorized request.")

if cancel_run_id is not None:
    run = api("GET", f"/repos/{REPOSITORY}/actions/runs/{cancel_run_id}", allowed=(200,))
    already_cancelled = (
        run.get("name") == "KDE Plasma authoritative KVM package build"
        and run.get("event") == "pull_request"
        and run.get("head_sha") == source_commit
        and run.get("status") == "completed"
        and run.get("conclusion") == "cancelled"
    )
    if not already_cancelled:
        valid_stale = (
            run.get("name") == "KDE Plasma authoritative KVM package build"
            and run.get("event") == "pull_request"
            and run.get("head_sha") == source_commit
            and run.get("status") == "queued"
            and run.get("conclusion") is None
        )
        if not valid_stale:
            raise SystemExit("Refusing to cancel a run that is not the exact queued stale gate.")
        jobs = api(
            "GET",
            f"/repos/{REPOSITORY}/actions/runs/{cancel_run_id}/jobs?per_page=100",
            allowed=(200,),
        )
        job_rows = jobs.get("jobs", [])
        if not job_rows or any(
            job.get("status") != "queued" or job.get("conclusion") is not None
            for job in job_rows
        ):
            raise SystemExit("Refusing cancellation because a stale-run job has started.")
        api("POST", f"/repos/{REPOSITORY}/actions/runs/{cancel_run_id}/cancel")
        deadline = time.monotonic() + 90
        while True:
            run = api(
                "GET",
                f"/repos/{REPOSITORY}/actions/runs/{cancel_run_id}",
                allowed=(200,),
            )
            if run.get("status") == "completed" and run.get("conclusion") == "cancelled":
                break
            if time.monotonic() >= deadline:
                raise SystemExit("Timed out waiting for stale queued run cancellation.")
            time.sleep(2)
    write_result("stale-run.txt", f"stale_run_cancelled={cancel_run_id}\n")

api(
    "DELETE",
    f"/repos/{REPOSITORY}/issues/{PR_NUMBER}/labels/ci%3Aplasma-package-build",
    allowed=(200, 204, 404),
)

control_dir = WORK_ROOT / control_run_id
checkout = control_dir / "repo"
if control_dir.exists():
    raise SystemExit(f"Control work directory already exists: {control_dir}")
control_dir.mkdir(mode=0o700)
os.chown(control_dir, operator.pw_uid, operator.pw_gid)

try:
    run_as_operator(["git", "init", "-q", str(checkout)])
    run_as_operator(
        ["git", "-C", str(checkout), "remote", "add", "origin", f"https://github.com/{REPOSITORY}.git"]
    )
    run_as_operator(
        ["git", "-C", str(checkout), "fetch", "-q", "--depth=1", "origin", f"refs/pull/{PR_NUMBER}/head"]
    )
    run_as_operator(["git", "-C", str(checkout), "checkout", "-q", "--detach", "FETCH_HEAD"])
    resolved_head = run_as_operator(["git", "-C", str(checkout), "rev-parse", "HEAD"]).stdout.strip()
    if resolved_head != source_commit:
        raise SystemExit("Ephemeral control checkout does not match source commit.")
    if run_as_operator(
        ["git", "-C", str(checkout), "status", "--porcelain", "--untracked-files=normal"]
    ).stdout:
        raise SystemExit("Ephemeral control checkout is not clean.")

    preflight_log = []
    for command in (
        ["scripts/check-kvm-host.sh"],
        ["scripts/with-libguestfs-runtime.sh", "true"],
    ):
        proc = run_as_operator(command, cwd=checkout)
        preflight_log.append(proc.stdout)
        preflight_log.append(proc.stderr)

    golden_tmp = control_dir / "golden-admission.txt"
    proc = run_as_operator(
        [
            "scripts/check-golden-image-provenance.sh",
            str(GOLDEN_IMAGE),
            str(golden_tmp),
        ],
        cwd=checkout,
        extra_env={"SUPRALINUX_GOLDEN_COMPAT_COMMIT": source_commit},
    )
    preflight_log.extend([proc.stdout, proc.stderr])
    write_result("host-preflight.log", "".join(preflight_log))
    write_result("golden-admission.txt", golden_tmp.read_text())

    if run_as_operator(
        ["git", "-C", str(checkout), "status", "--porcelain", "--untracked-files=normal"]
    ).stdout:
        raise SystemExit("Host preflight modified the exact control checkout.")

    write_result(
        "preflight-result.txt",
        "\n".join(
            [
                "state=PASS",
                "scope=host-authoritative-control-preflight",
                f"mode={request['mode']}",
                f"gate={request['gate']}",
                f"source_commit={source_commit}",
                f"operator_user={operator.pw_name}",
                f"runner_group_id={runner_group_id}",
                "package_attempt_effect=none-before-execute",
                "",
            ]
        ),
    )

    if request["mode"] == "preflight":
        print("HOST_AUTHORITATIVE_PREFLIGHT=PASS")
        raise SystemExit(0)

    env = os.environ.copy()
    env.update({
        "HOME": operator.pw_dir,
        "USER": operator.pw_name,
        "LOGNAME": operator.pw_name,
        "SUPRALINUX_GITHUB_TOKEN": token,
        "SUPRALINUX_RUNNER_GROUP_ID": str(runner_group_id),
        "SUPRALINUX_REPOSITORY": REPOSITORY,
        "SUPRALINUX_PR_NUMBER": str(PR_NUMBER),
    })
    log_path = result_dir / "jit-gate.log"
    with log_path.open("w") as log:
        process = subprocess.Popen(
            ["scripts/run-kvm-jit-gate.sh", request["gate"]],
            cwd=checkout,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=demote,
        )
        assert process.stdout is not None
        for line in process.stdout:
            log.write(line)
            log.flush()
            print(line, end="", flush=True)
        gate_rc = process.wait()
    os.chmod(log_path, 0o600)
    os.chown(log_path, runner_pw.pw_uid, runner_pw.pw_gid)
    write_result(
        "execute-result.txt",
        "\n".join(
            [
                f"state={'PASS' if gate_rc == 0 else 'FAIL'}",
                f"gate_exit_code={gate_rc}",
                f"gate={request['gate']}",
                f"source_commit={source_commit}",
                "",
            ]
        ),
    )
    raise SystemExit(gate_rc)
finally:
    token = ""
    if control_dir.exists():
        shutil.rmtree(control_dir)
