#!/usr/bin/env python3
import grp
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
    "cancel_run_head_sha", "source_commit", "control_run_id",
}
unknown = set(request) - allowed_keys
if unknown:
    raise SystemExit(f"Unknown authoritative request keys: {sorted(unknown)}")
if request.get("schema") != 1:
    raise SystemExit("Unsupported request schema.")
if request.get("mode") not in {"diagnose", "repair-host", "preflight", "rebuild-golden", "execute"}:
    raise SystemExit("Unsupported control mode.")
if request.get("gate") != "plasma-package-build":
    raise SystemExit("Unsupported authoritative gate.")

source_commit = request.get("source_commit")
control_run_id = request.get("control_run_id")
runner_group_id = request.get("runner_group_id")
cancel_run_id = request.get("cancel_run_id")
cancel_run_head_sha = request.get("cancel_run_head_sha")
if not isinstance(source_commit, str) or len(source_commit) != 40 or any(c not in "0123456789abcdef" for c in source_commit):
    raise SystemExit("Invalid source commit.")
if not isinstance(control_run_id, str) or not control_run_id.isdigit():
    raise SystemExit("Invalid control run id.")
if not isinstance(runner_group_id, int) or runner_group_id <= 0:
    raise SystemExit("Invalid runner group id.")
if cancel_run_id is not None and (not isinstance(cancel_run_id, int) or cancel_run_id <= 0):
    raise SystemExit("Invalid cancellation run id.")
if cancel_run_id is None:
    if cancel_run_head_sha is not None:
        raise SystemExit("Cancellation head SHA requires a cancellation run id.")
else:
    if (
        not isinstance(cancel_run_head_sha, str)
        or len(cancel_run_head_sha) != 40
        or any(c not in "0123456789abcdef" for c in cancel_run_head_sha)
    ):
        raise SystemExit("Invalid cancellation head SHA.")
if request["mode"] in {"diagnose", "repair-host", "rebuild-golden", "execute"} and (
    cancel_run_id is not None or cancel_run_head_sha is not None
):
    raise SystemExit(f"{request['mode']} mode refuses stale-run cancellation.")

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

KVM_RUNTIME_PROBE = r"""
import fcntl
import json
import os

path = "/dev/kvm"
report = {
    "uid": os.getuid(),
    "euid": os.geteuid(),
    "gid": os.getgid(),
    "egid": os.getegid(),
    "groups": os.getgroups(),
    "access_real_rw": os.access(path, os.R_OK | os.W_OK),
}
try:
    report["access_effective_rw"] = os.access(
        path, os.R_OK | os.W_OK, effective_ids=True
    )
except (NotImplementedError, TypeError):
    report["access_effective_rw"] = "unsupported"
try:
    fd = os.open(path, os.O_RDWR | os.O_CLOEXEC)
except OSError as exc:
    report["open_ok"] = False
    report["open_errno"] = exc.errno
    report["open_error"] = exc.strerror
else:
    report["open_ok"] = True
    try:
        report["kvm_api_version"] = fcntl.ioctl(fd, 0xAE00, 0)
    except OSError as exc:
        report["ioctl_errno"] = exc.errno
        report["ioctl_error"] = exc.strerror
    finally:
        os.close(fd)
print(json.dumps(report, sort_keys=True))
"""

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

def make_demote(extra_groups=()):
    def demote():
        os.initgroups(operator.pw_name, operator.pw_gid)
        groups = set(os.getgroups())
        groups.update(extra_groups)
        os.setgroups(sorted(groups))
        os.setgid(operator.pw_gid)
        os.setuid(operator.pw_uid)
    return demote

def operator_environment(extra_env=None):
    env = os.environ.copy()
    env.update({
        "HOME": operator.pw_dir,
        "USER": operator.pw_name,
        "LOGNAME": operator.pw_name,
    })
    if extra_env:
        env.update(extra_env)
    return env

def run_as_operator(
    args, *, cwd=None, extra_env=None, extra_groups=(), check=True, capture_output=True
):
    return subprocess.run(
        args,
        cwd=cwd,
        env=operator_environment(extra_env),
        check=check,
        capture_output=capture_output,
        text=True,
        preexec_fn=make_demote(extra_groups),
    )

def stream_as_operator(args, log_path, *, cwd=None, extra_env=None, extra_groups=()):
    with log_path.open("w") as log:
        process = subprocess.Popen(
            args,
            cwd=cwd,
            env=operator_environment(extra_env),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=make_demote(extra_groups),
        )
        assert process.stdout is not None
        for line in process.stdout:
            log.write(line)
            log.flush()
            print(line, end="", flush=True)
        rc = process.wait()
    os.chmod(log_path, 0o600)
    os.chown(log_path, runner_pw.pw_uid, runner_pw.pw_gid)
    return rc

libvirt_group = pwd.getpwnam("libvirt-qemu").pw_gid
group_names = set(run_as_operator(["id", "-nG"]).stdout.split())
libvirt_group_name = grp.getgrgid(libvirt_group).gr_name
if libvirt_group_name not in group_names:
    raise SystemExit("Resolved operator lacks libvirt QEMU group.")

kvm_stat = os.stat("/dev/kvm")
kvm_group = kvm_stat.st_gid
kvm_group_name = grp.getgrgid(kvm_group).gr_name
privileged_groups = tuple(sorted({libvirt_group, kvm_group}))
write_result(
    "operator-diagnostic.txt",
    "\n".join(
        [
            f"operator_user={operator.pw_name}",
            f"operator_groups={','.join(sorted(group_names))}",
            f"kvm_gid={kvm_group}",
            f"kvm_group={kvm_group_name}",
            f"libvirt_qemu_gid={libvirt_group}",
            f"libvirt_qemu_group={libvirt_group_name}",
            "persistent_group_membership_changed=no",
            "privilege_scope=child-process-only",
            "",
        ]
    ),
)

if request["mode"] == "diagnose":
    def capture(label, args, *, as_operator=False, extra_groups=()):
        try:
            if as_operator:
                proc = run_as_operator(
                    args,
                    extra_groups=extra_groups,
                    check=False,
                    capture_output=True,
                )
            else:
                proc = subprocess.run(
                    args,
                    check=False,
                    capture_output=True,
                    text=True,
                )
            return "\n".join(
                [
                    f"=== {label} ===",
                    f"argv={json.dumps(args)}",
                    f"rc={proc.returncode}",
                    "--- stdout ---",
                    proc.stdout.rstrip(),
                    "--- stderr ---",
                    proc.stderr.rstrip(),
                    "",
                ]
            )
        except Exception as exc:
            return "\n".join(
                [
                    f"=== {label} ===",
                    f"exception={type(exc).__name__}: {exc}",
                    "",
                ]
            )


    sections = []
    sections.append(capture("root-id", ["id", "-a"]))
    sections.append(capture("operator-id-normal", ["id", "-a"], as_operator=True))
    sections.append(
        capture(
            "operator-id-scoped-groups",
            ["id", "-a"],
            as_operator=True,
            extra_groups=privileged_groups,
        )
    )
    sections.append(
        capture(
            "dev-kvm-stat",
            ["stat", "-Lc", "%A %a %U %G %u %g %t:%T %n", "/dev/kvm"],
        )
    )
    if shutil.which("getfacl"):
        sections.append(capture("dev-kvm-acl", ["getfacl", "-p", "/dev/kvm"]))
    sections.append(capture("root-kvm-open", ["python3", "-c", KVM_RUNTIME_PROBE]))
    sections.append(
        capture(
            "operator-kvm-open-normal",
            ["python3", "-c", KVM_RUNTIME_PROBE],
            as_operator=True,
        )
    )
    sections.append(
        capture(
            "operator-kvm-open-scoped-groups",
            ["python3", "-c", KVM_RUNTIME_PROBE],
            as_operator=True,
            extra_groups=privileged_groups,
        )
    )
    sections.append(capture("root-cgroup", ["cat", "/proc/self/cgroup"]))
    sections.append(
        capture(
            "operator-cgroup",
            ["cat", "/proc/self/cgroup"],
            as_operator=True,
            extra_groups=privileged_groups,
        )
    )
    sections.append(capture("root-lsm", ["cat", "/proc/self/attr/current"]))
    sections.append(
        capture(
            "operator-lsm",
            ["cat", "/proc/self/attr/current"],
            as_operator=True,
            extra_groups=privileged_groups,
        )
    )
    sections.append(
        capture(
            "operator-check-kvm-host",
            ["scripts/check-kvm-host.sh"],
            as_operator=True,
            extra_groups=privileged_groups,
        )
    )
    sections.append(
        capture(
            "operator-check-kvm-network-userspace",
            ["python3", "scripts/check-kvm-network.py", "--userspace"],
            as_operator=True,
            extra_groups=privileged_groups,
        )
    )
    sections.append(capture("host-default-routes", ["ip", "-json", "route", "show", "default"]))
    default_routes = subprocess.run(
        ["ip", "-json", "route", "show", "default"],
        check=False,
        capture_output=True,
        text=True,
    )
    try:
        default_devices = sorted(
            {
                route.get("dev")
                for route in json.loads(default_routes.stdout or "[]")
                if route.get("dev")
            }
        )
    except json.JSONDecodeError:
        default_devices = []
    for device in default_devices:
        sections.append(capture(f"host-{device}-driver", ["ethtool", "-i", device]))
        sections.append(capture(f"host-{device}-features", ["ethtool", "-k", device]))
        sections.append(capture(f"host-{device}-address", ["ip", "-json", "address", "show", "dev", device]))
        carrier = Path("/sys/class/net") / device / "carrier"
        if carrier.is_file():
            sections.append(capture(f"host-{device}-carrier", ["cat", str(carrier)]))
    sections.append(capture("host-uptime-since", ["uptime", "-s"]))
    kernel_release = os.uname().release
    runtime_dir = Path("/var/lib/supralinux/images/libguestfs-runtime") / kernel_release
    runtime_provenance = runtime_dir / "provenance.txt"
    source_kernel = Path("/boot") / f"vmlinuz-{kernel_release}"
    modules_dep = Path("/lib/modules") / kernel_release / "modules.dep"
    sections.append(capture("libguestfs-runtime-dir", ["stat", "-Lc", "%A %a %U %G %u %g %n", str(runtime_dir)]))
    sections.append(capture("libguestfs-runtime-cache", ["stat", "-Lc", "%A %a %U %G %u %g %n", str(runtime_dir / "cache")]))
    sections.append(capture("libguestfs-runtime-provenance", ["cat", str(runtime_provenance)]))
    sections.append(capture("libguestfs-source-kernel-stat", ["stat", "-c", "%s:%Y:%Z:%i", str(source_kernel)]))
    sections.append(capture("libguestfs-runtime-kernel-sha256", ["sha256sum", str(runtime_dir / "vmlinuz")]))
    sections.append(capture("libguestfs-modules-dep-sha256", ["sha256sum", str(modules_dep)]))
    sections.append(
        capture(
            "runner-service-units",
            [
                "systemctl",
                "--no-legend",
                "--plain",
                "list-units",
                "actions.runner.SupraLINUX-SupraLINUX.*.service",
            ],
        )
    )
    units = subprocess.run(
        [
            "systemctl",
            "--no-legend",
            "--plain",
            "list-units",
            "actions.runner.SupraLINUX-SupraLINUX.*.service",
        ],
        check=False,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    if units:
        unit = units[0].split()[0]
        sections.append(
            capture(
                "runner-service-security",
                [
                    "systemctl",
                    "show",
                    unit,
                    "--property=User",
                    "--property=Group",
                    "--property=SupplementaryGroups",
                    "--property=PrivateDevices",
                    "--property=DevicePolicy",
                    "--property=DeviceAllow",
                    "--property=NoNewPrivileges",
                    "--property=ProtectSystem",
                    "--property=ProtectHome",
                    "--property=RestrictAddressFamilies",
                    "--property=CapabilityBoundingSet",
                    "--property=AmbientCapabilities",
                ],
            )
        )

    write_result("kvm-access-diagnostic.txt", "\n".join(sections))
    write_result(
        "diagnose-result.txt",
        "\n".join(
            [
                "state=PASS",
                "scope=host-authoritative-control-diagnostic-collection",
                f"source_commit={source_commit}",
                f"operator_user={operator.pw_name}",
                "github_token_requested=no",
                "github_api_mutation=no",
                "jit_invoked=no",
                "vm_created=no",
                "package_attempt_effect=none",
                "",
            ]
        ),
    )
    print("HOST_AUTHORITATIVE_DIAGNOSTIC_COLLECTION=PASS")
    raise SystemExit(0)
kvm_runtime = run_as_operator(
    ["python3", "-c", KVM_RUNTIME_PROBE],
    extra_groups=privileged_groups,
)
try:
    kvm_runtime_result = json.loads(kvm_runtime.stdout)
except json.JSONDecodeError as exc:
    raise SystemExit(f"Invalid KVM runtime probe output: {exc}")
if not (
    kvm_runtime_result.get("open_ok") is True
    and kvm_runtime_result.get("kvm_api_version") == 12
):
    raise SystemExit(
        "Certified host operator cannot open /dev/kvm O_RDWR and query KVM API version."
    )
write_result(
    "kvm-runtime-admission.json",
    json.dumps(kvm_runtime_result, indent=2, sort_keys=True) + "\n",
)
if request["mode"] == "repair-host":
    repair = subprocess.run(
        ["/usr/local/libexec/supralinux-restore-kvm-host-network-safety"],
        check=False,
        capture_output=True,
        text=True,
    )
    write_result("host-network-repair.stdout", repair.stdout)
    write_result("host-network-repair.stderr", repair.stderr)
    state = "PASS" if repair.returncode == 0 else "INFRA_INVALID"
    if repair.returncode == 0:
        payload = json.loads(repair.stdout)
        if not (
            payload.get("state") == "PASS"
            and payload.get("package_attempt_effect") == "none"
            and payload.get("persistent_change") is False
            and payload.get("vm_created") is False
            and payload.get("jit_invoked") is False
        ):
            raise SystemExit("Host network repair returned an invalid PASS receipt.")
    write_result(
        "repair-host-result.txt",
        "\n".join(
            [
                f"state={state}",
                f"exit_code={repair.returncode}",
                f"source_commit={source_commit}",
                "scope=e1000e-runtime-offload-safety-restore",
                "github_token_requested=no",
                "github_api_mutation=no",
                "vm_created=no",
                "jit_invoked=no",
                "package_attempt_effect=none",
                "",
            ]
        ),
    )
    if repair.returncode != 0:
        raise SystemExit(repair.returncode)
    print("HOST_NETWORK_SAFETY_REPAIR=PASS")
    raise SystemExit(0)
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
        and run.get("head_sha") == cancel_run_head_sha
        and run.get("status") == "completed"
        and run.get("conclusion") == "cancelled"
    )
    if not already_cancelled:
        valid_stale = (
            run.get("name") == "KDE Plasma authoritative KVM package build"
            and run.get("event") == "pull_request"
            and run.get("head_sha") == cancel_run_head_sha
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

package_build_label_present = any(
    label.get("name") == "ci:plasma-package-build"
    for label in pr.get("labels", [])
    if isinstance(label, dict)
)
if package_build_label_present:
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
        proc = run_as_operator(command, cwd=checkout, extra_groups=privileged_groups)
        preflight_log.append(proc.stdout)
        preflight_log.append(proc.stderr)

    if request["mode"] == "rebuild-golden":
        write_result("host-preflight.log", "".join(preflight_log))
        network_preflight_log = result_dir / "golden-network-preflight.log"
        network_preflight_rc = stream_as_operator(
            ["scripts/check-golden-build-network-preflight.sh"],
            network_preflight_log,
            cwd=checkout,
            extra_groups=privileged_groups,
        )
        if network_preflight_rc != 0:
            write_result(
                "golden-network-preflight-result.txt",
                "\n".join(
                    [
                        "state=INFRA_INVALID",
                        f"exit_code={network_preflight_rc}",
                        f"source_commit={source_commit}",
                        "golden_rebuild_started=no",
                        "package_attempt_effect=none",
                        "",
                    ]
                ),
            )
            raise SystemExit(network_preflight_rc)
        write_result(
            "golden-network-preflight-result.txt",
            "\n".join(
                [
                    "state=PASS",
                    "exit_code=0",
                    f"source_commit={source_commit}",
                    "golden_rebuild_authorized=yes",
                    "package_attempt_effect=none",
                    "",
                ]
            ),
        )
        rebuild_log = result_dir / "golden-rebuild.log"
        rebuild_rc = stream_as_operator(
            ["scripts/build-authoritative-runner-image.sh"],
            rebuild_log,
            cwd=checkout,
            extra_env={
                "SUPRALINUX_SOURCE_COMMIT": source_commit,
                "SUPRALINUX_GOLDEN_IMAGE": str(GOLDEN_IMAGE),
                "SUPRALINUX_REPLACE_GOLDEN_IMAGE": "1",
            },
            extra_groups=privileged_groups,
        )
        if rebuild_rc != 0:
            write_result(
                "golden-rebuild-result.txt",
                "\n".join(
                    [
                        "state=INFRA_INVALID",
                        f"exit_code={rebuild_rc}",
                        f"source_commit={source_commit}",
                        "package_attempt_effect=none",
                        "jit_invoked=no",
                        "",
                    ]
                ),
            )
            raise SystemExit(rebuild_rc)

        rebuild_admission = control_dir / "golden-rebuild-admission.txt"
        proc = run_as_operator(
            [
                "scripts/check-golden-image-provenance.sh",
                str(GOLDEN_IMAGE),
                str(rebuild_admission),
            ],
            cwd=checkout,
            extra_env={"SUPRALINUX_GOLDEN_COMPAT_COMMIT": source_commit},
            extra_groups=privileged_groups,
        )
        write_result("golden-rebuild-admission.txt", rebuild_admission.read_text())
        provenance = Path(str(GOLDEN_IMAGE) + ".provenance.txt")
        write_result("golden-rebuild-provenance.txt", provenance.read_text())
        write_result(
            "golden-rebuild-result.txt",
            "\n".join(
                [
                    "state=PASS",
                    "exit_code=0",
                    f"source_commit={source_commit}",
                    "golden_input_compatibility=PASS",
                    "package_attempt_effect=none",
                    "jit_invoked=no",
                    "",
                ]
            ),
        )
        print("HOST_AUTHORITATIVE_GOLDEN_REBUILD=PASS")
        raise SystemExit(0)

    golden_tmp = control_dir / "golden-admission.txt"
    proc = run_as_operator(
        [
            "scripts/check-golden-image-provenance.sh",
            str(GOLDEN_IMAGE),
            str(golden_tmp),
        ],
        cwd=checkout,
        extra_env={"SUPRALINUX_GOLDEN_COMPAT_COMMIT": source_commit},
        extra_groups=privileged_groups,
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

    log_path = result_dir / "jit-gate.log"
    gate_rc = stream_as_operator(
        ["scripts/run-kvm-jit-gate.sh", request["gate"]],
        log_path,
        cwd=checkout,
        extra_env={
            "SUPRALINUX_GITHUB_TOKEN": token,
            "SUPRALINUX_RUNNER_GROUP_ID": str(runner_group_id),
            "SUPRALINUX_REPOSITORY": REPOSITORY,
            "SUPRALINUX_PR_NUMBER": str(PR_NUMBER),
        },
        extra_groups=privileged_groups,
    )
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
