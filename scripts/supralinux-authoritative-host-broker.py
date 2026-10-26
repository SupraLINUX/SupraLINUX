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
CLOSE_EVIDENCE_HELPER = Path("/usr/local/libexec/supralinux-host-close-package-evidence")
HOST_EVIDENCE_ROOT = Path("/var/lib/supralinux/evidence/host-kvm")
PERSISTENT_ARTIFACT_ROOT = Path("/var/lib/supralinux/artifacts")

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
    "evidence_node", "evidence_package_run_id", "evidence_package_job_id",
    "evidence_package_artifact_id", "evidence_package_artifact_sha256",
    "evidence_host_manifest_sha256", "evidence_incident_cause",
    "evidence_incident_repair",
}
unknown = set(request) - allowed_keys
if unknown:
    raise SystemExit(f"Unknown authoritative request keys: {sorted(unknown)}")
if request.get("schema") != 1:
    raise SystemExit("Unsupported request schema.")
if request.get("mode") not in {
    "diagnose", "repair-host", "preflight", "rebuild-golden", "execute",
    "execute-and-publish-pass",
    "close-evidence-check", "close-evidence",
    "publish-evidence-check", "publish-evidence",
}:
    raise SystemExit("Unsupported control mode.")
if request.get("gate") != "plasma-package-build":
    raise SystemExit("Unsupported authoritative gate.")

source_commit = request.get("source_commit")
control_run_id = request.get("control_run_id")
runner_group_id = request.get("runner_group_id")
cancel_run_id = request.get("cancel_run_id")
cancel_run_head_sha = request.get("cancel_run_head_sha")
evidence_node = request.get("evidence_node")
evidence_package_run_id = request.get("evidence_package_run_id")
evidence_package_job_id = request.get("evidence_package_job_id")
evidence_package_artifact_id = request.get("evidence_package_artifact_id")
evidence_package_artifact_sha256 = request.get("evidence_package_artifact_sha256")
evidence_host_manifest_sha256 = request.get("evidence_host_manifest_sha256")
evidence_incident_cause = request.get("evidence_incident_cause")
evidence_incident_repair = request.get("evidence_incident_repair")
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
close_modes = {"close-evidence-check", "close-evidence", "publish-evidence-check", "publish-evidence"}
close_values = (
    evidence_node,
    evidence_package_run_id,
    evidence_package_job_id,
    evidence_package_artifact_id,
    evidence_package_artifact_sha256,
    evidence_host_manifest_sha256,
    evidence_incident_cause,
    evidence_incident_repair,
)
if request["mode"] in close_modes:
    if not isinstance(evidence_node, str) or not evidence_node or len(evidence_node) > 64:
        raise SystemExit("Invalid evidence node.")
    if any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789+.-" for ch in evidence_node):
        raise SystemExit("Invalid evidence node.")
    if evidence_node[0] not in "abcdefghijklmnopqrstuvwxyz0123456789":
        raise SystemExit("Invalid evidence node.")
    for label, value in (
        ("package run", evidence_package_run_id),
        ("package job", evidence_package_job_id),
        ("package artifact", evidence_package_artifact_id),
    ):
        if not isinstance(value, int) or value <= 0:
            raise SystemExit(f"Invalid evidence {label} id.")
    for label, value in (
        ("package artifact", evidence_package_artifact_sha256),
        ("host manifest", evidence_host_manifest_sha256),
    ):
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(ch not in "0123456789abcdef" for ch in value)
        ):
            raise SystemExit(f"Invalid evidence {label} SHA-256.")
    incident_values = (evidence_incident_cause, evidence_incident_repair)
    if (incident_values[0] is None) != (incident_values[1] is None):
        raise SystemExit("Evidence incident cause and repair must be supplied together.")
    for label, value in (
        ("incident cause", evidence_incident_cause),
        ("incident repair", evidence_incident_repair),
    ):
        if value is not None and (
            not isinstance(value, str)
            or not value.strip()
            or value != value.strip()
            or len(value) > 4000
            or "\x00" in value
        ):
            raise SystemExit(f"Invalid evidence {label}.")
else:
    if any(value is not None for value in close_values):
        raise SystemExit("Evidence closure fields are valid only for evidence closure modes.")

if request["mode"] in {
    "diagnose", "repair-host", "rebuild-golden", "execute", "execute-and-publish-pass",
    "close-evidence-check", "close-evidence", "publish-evidence-check", "publish-evidence",
} and (
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

def run_package_closure(
    *,
    helper_mode,
    node,
    package_run_id,
    package_job_id,
    package_artifact_id,
    package_artifact_sha256,
    host_manifest_sha256,
    artifact_root,
    work_root,
    output_dir,
    log_path,
):
    output_dir.mkdir(parents=True, mode=0o700, exist_ok=False)
    os.chown(output_dir, operator.pw_uid, operator.pw_gid)
    command = [
        str(CLOSE_EVIDENCE_HELPER),
        "--mode", helper_mode,
        "--source-commit", source_commit,
        "--control-run-id", control_run_id,
        "--node", node,
        "--package-run-id", str(package_run_id),
        "--package-job-id", str(package_job_id),
        "--package-artifact-id", str(package_artifact_id),
        "--package-artifact-sha256", package_artifact_sha256,
        "--host-manifest-sha256", host_manifest_sha256,
        "--host-evidence-root", str(HOST_EVIDENCE_ROOT),
        "--artifact-root", str(artifact_root),
        "--work-root", str(work_root),
        "--output-dir", str(output_dir),
    ]
    rc = stream_as_operator(command, log_path)
    if rc != 0:
        raise SystemExit(rc)
    return output_dir


if request["mode"] in {"close-evidence-check", "close-evidence", "publish-evidence-check", "publish-evidence"}:
    if not CLOSE_EVIDENCE_HELPER.is_file() or not os.access(CLOSE_EVIDENCE_HELPER, os.X_OK):
        raise SystemExit("Installed authoritative evidence closure helper is missing.")

    close_root = WORK_ROOT / control_run_id
    if close_root.exists():
        raise SystemExit(f"Evidence closure work directory already exists: {close_root}")
    close_root.mkdir(mode=0o700)
    os.chown(close_root, operator.pw_uid, operator.pw_gid)

    close_output = close_root / "output"
    close_output.mkdir(mode=0o700)
    os.chown(close_output, operator.pw_uid, operator.pw_gid)
    close_work = close_root / "work"

    helper_mode = {
        "close-evidence-check": "check",
        "close-evidence": "close",
        "publish-evidence-check": "publish-check",
        "publish-evidence": "publish",
    }[request["mode"]]
    if request["mode"] in {"close-evidence-check", "publish-evidence-check"}:
        artifact_root = close_root / "artifact-replay"
        artifact_root.mkdir(mode=0o700)
        os.chown(artifact_root, operator.pw_uid, operator.pw_gid)
    else:
        if not PERSISTENT_ARTIFACT_ROOT.exists():
            PERSISTENT_ARTIFACT_ROOT.mkdir(parents=True, mode=0o700)
            os.chown(PERSISTENT_ARTIFACT_ROOT, operator.pw_uid, operator.pw_gid)
        run_as_operator(["test", "-d", str(PERSISTENT_ARTIFACT_ROOT)])
        run_as_operator(["test", "-w", str(PERSISTENT_ARTIFACT_ROOT)])
        artifact_root = PERSISTENT_ARTIFACT_ROOT

    close_log = result_dir / "close-evidence.log"
    close_rc = 125
    try:
        close_command = [
            str(CLOSE_EVIDENCE_HELPER),
            "--mode", helper_mode,
            "--source-commit", source_commit,
            "--control-run-id", control_run_id,
            "--node", evidence_node,
            "--package-run-id", str(evidence_package_run_id),
            "--package-job-id", str(evidence_package_job_id),
            "--package-artifact-id", str(evidence_package_artifact_id),
            "--package-artifact-sha256", evidence_package_artifact_sha256,
            "--host-manifest-sha256", evidence_host_manifest_sha256,
            "--host-evidence-root", str(HOST_EVIDENCE_ROOT),
            "--artifact-root", str(artifact_root),
            "--work-root", str(close_work),
            "--output-dir", str(close_output),
        ]
        if evidence_incident_cause is not None:
            close_command.extend(
                [
                    "--incident-cause", evidence_incident_cause,
                    "--incident-repair", evidence_incident_repair,
                ]
            )
        close_rc = stream_as_operator(
            close_command,
            close_log,
        )
        if close_output.exists():
            if any(path.is_symlink() for path in close_output.rglob("*")):
                raise SystemExit("Evidence closure output contains a symlink.")
            destination = result_dir / "evidence-closure"
            shutil.copytree(close_output, destination)
            for path in [destination, *destination.rglob("*")]:
                os.chown(path, runner_pw.pw_uid, runner_pw.pw_gid)
                os.chmod(path, 0o700 if path.is_dir() else 0o600)
    finally:
        if close_root.exists():
            shutil.rmtree(close_root)

    write_result(
        "close-evidence-control-result.txt",
        "\n".join(
            [
                f"state={'PASS' if close_rc == 0 else 'FAIL'}",
                f"exit_code={close_rc}",
                f"mode={request['mode']}",
                f"source_commit={source_commit}",
                f"node={evidence_node}",
                f"package_run_id={evidence_package_run_id}",
                "vm_created=no",
                "jit_invoked=no",
                "package_attempt_effect=none",
                "",
            ]
        ),
    )
    if close_rc != 0:
        raise SystemExit(close_rc)
    print("HOST_AUTHORITATIVE_EVIDENCE_CLOSURE=PASS")
    raise SystemExit(0)

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

host_control_label_present = any(
    label.get("name") == "ci:host-workspace"
    for label in pr.get("labels", [])
    if isinstance(label, dict)
)
if host_control_label_present:
    api(
        "DELETE",
        f"/repos/{REPOSITORY}/issues/{PR_NUMBER}/labels/ci%3Ahost-workspace",
        allowed=(200, 204, 404),
    )

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
    gate_receipt = control_dir / "gate-receipt.json"
    gate_rc = stream_as_operator(
        ["scripts/run-kvm-jit-gate.sh", request["gate"]],
        log_path,
        cwd=checkout,
        extra_env={
            "SUPRALINUX_GITHUB_TOKEN": token,
            "SUPRALINUX_RUNNER_GROUP_ID": str(runner_group_id),
            "SUPRALINUX_REPOSITORY": REPOSITORY,
            "SUPRALINUX_PR_NUMBER": str(PR_NUMBER),
            "SUPRALINUX_GATE_RECEIPT_PATH": str(gate_receipt),
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
    if gate_rc != 0 or request["mode"] != "execute-and-publish-pass":
        raise SystemExit(gate_rc)

    if not gate_receipt.is_file() or gate_receipt.is_symlink():
        raise SystemExit("Successful guarded execution did not return a regular gate receipt.")
    receipt = json.loads(gate_receipt.read_text())
    if not (
        receipt.get("schema") == 1
        and receipt.get("gate") == request["gate"]
        and receipt.get("source_commit") == source_commit
        and receipt.get("exit_code") == 0
        and isinstance(receipt.get("workflow_run_id"), int)
        and receipt["workflow_run_id"] > 0
    ):
        raise SystemExit("Invalid successful gate receipt.")
    host_dir = Path(receipt.get("evidence_dir", ""))
    try:
        host_dir.resolve().relative_to(HOST_EVIDENCE_ROOT.resolve())
    except (OSError, ValueError):
        raise SystemExit("Gate receipt points outside the authoritative host evidence root.")
    manifest_path = host_dir / "evidence-sha256.txt"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise SystemExit("Gate receipt host evidence manifest is missing.")
    host_manifest_sha = subprocess.check_output(
        ["sha256sum", str(manifest_path)], text=True
    ).split()[0]
    if host_manifest_sha != receipt.get("host_manifest_sha256"):
        raise SystemExit("Gate receipt host evidence manifest digest mismatch.")

    campaign = json.loads((checkout / "manifests/kde-plasma-package-build.json").read_text())
    authorized = campaign.get("authorized_nodes", [])
    if (
        campaign.get("execution_mode") != "guarded-build"
        or len(authorized) != 1
        or campaign["nodes"][authorized[0]].get("state") != "build-pending"
    ):
        raise SystemExit("Automatic PASS publication requires one guarded build-pending node.")
    node = authorized[0]
    child_run_id = receipt["workflow_run_id"]
    child = api(
        "GET",
        f"/repos/{REPOSITORY}/actions/runs/{child_run_id}",
        allowed=(200,),
    )
    if not (
        child.get("name") == "KDE Plasma authoritative KVM package build"
        and child.get("head_sha") == source_commit
        and child.get("status") == "completed"
        and child.get("conclusion") == "success"
    ):
        raise SystemExit("Gate receipt child workflow is not the exact successful package run.")
    jobs = api(
        "GET",
        f"/repos/{REPOSITORY}/actions/runs/{child_run_id}/jobs?per_page=100",
        allowed=(200,),
    ).get("jobs", [])
    package_jobs = [
        job for job in jobs
        if job.get("name") == "Reviewed Plasma package on KVM guest"
        and job.get("status") == "completed"
        and job.get("conclusion") == "success"
    ]
    if len(package_jobs) != 1:
        raise SystemExit("Successful child run does not have exactly one package job.")
    package_job_id = package_jobs[0]["id"]

    artifacts = api(
        "GET",
        f"/repos/{REPOSITORY}/actions/runs/{child_run_id}/artifacts?per_page=100",
        allowed=(200,),
    ).get("artifacts", [])
    expected_artifact_name = f"authoritative-plasma-package-{source_commit}"
    package_artifacts = [
        artifact for artifact in artifacts
        if artifact.get("name") == expected_artifact_name
        and artifact.get("expired") is False
    ]
    if len(package_artifacts) != 1:
        raise SystemExit("Successful child run does not have exactly one package artifact.")
    artifact = package_artifacts[0]
    digest = artifact.get("digest", "")
    if (
        not isinstance(digest, str)
        or not digest.startswith("sha256:")
        or len(digest) != 71
        or any(ch not in "0123456789abcdef" for ch in digest[7:])
    ):
        raise SystemExit("Package artifact lacks an authenticated SHA-256 digest.")
    package_artifact_sha = digest[7:]
    package_artifact_id = artifact["id"]

    if not CLOSE_EVIDENCE_HELPER.is_file() or not os.access(CLOSE_EVIDENCE_HELPER, os.X_OK):
        raise SystemExit("Installed authoritative evidence closure helper is missing.")
    auto_root = control_dir / "auto-close"
    auto_root.mkdir(mode=0o700)
    os.chown(auto_root, operator.pw_uid, operator.pw_gid)

    check_artifacts = auto_root / "check-artifacts"
    check_artifacts.mkdir(mode=0o700)
    os.chown(check_artifacts, operator.pw_uid, operator.pw_gid)
    check_output = run_package_closure(
        helper_mode="publish-check",
        node=node,
        package_run_id=child_run_id,
        package_job_id=package_job_id,
        package_artifact_id=package_artifact_id,
        package_artifact_sha256=package_artifact_sha,
        host_manifest_sha256=host_manifest_sha,
        artifact_root=check_artifacts,
        work_root=auto_root / "check-work",
        output_dir=auto_root / "check-output",
        log_path=result_dir / "auto-close-check.log",
    )
    shutil.copytree(check_output, result_dir / "auto-close-check")

    if not PERSISTENT_ARTIFACT_ROOT.exists():
        PERSISTENT_ARTIFACT_ROOT.mkdir(parents=True, mode=0o700)
        os.chown(PERSISTENT_ARTIFACT_ROOT, operator.pw_uid, operator.pw_gid)
    run_as_operator(["test", "-d", str(PERSISTENT_ARTIFACT_ROOT)])
    run_as_operator(["test", "-w", str(PERSISTENT_ARTIFACT_ROOT)])
    publish_output = run_package_closure(
        helper_mode="publish",
        node=node,
        package_run_id=child_run_id,
        package_job_id=package_job_id,
        package_artifact_id=package_artifact_id,
        package_artifact_sha256=package_artifact_sha,
        host_manifest_sha256=host_manifest_sha,
        artifact_root=PERSISTENT_ARTIFACT_ROOT,
        work_root=auto_root / "publish-work",
        output_dir=auto_root / "publish-output",
        log_path=result_dir / "auto-close-publish.log",
    )
    shutil.copytree(publish_output, result_dir / "auto-close-publish")
    write_result(
        "auto-close-result.txt",
        "\n".join(
            [
                "state=PASS",
                "mode=execute-and-publish-pass",
                f"node={node}",
                f"package_run_id={child_run_id}",
                f"package_job_id={package_job_id}",
                f"package_artifact_id={package_artifact_id}",
                f"package_artifact_sha256={package_artifact_sha}",
                f"host_manifest_sha256={host_manifest_sha}",
                "publish_check=PASS",
                "publish=PASS",
                "",
            ]
        ),
    )
    print("HOST_AUTHORITATIVE_EXECUTE_AND_PUBLISH_PASS=PASS")
    raise SystemExit(0)
finally:
    token = ""
    if control_dir.exists():
        shutil.rmtree(control_dir)
