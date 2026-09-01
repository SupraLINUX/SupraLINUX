#!/usr/bin/env python3
from __future__ import annotations

import argparse
import glob
import http.client
import json
import os
import socket
import sys
from pathlib import Path
from typing import Any, NoReturn
from urllib.parse import quote

DOCKER_SOCKET = "/var/run/docker.sock"
APPARMOR_PROFILE = "supralinux-ksq-unshare"
SECURITY_OPT = ["seccomp=unconfined", f"apparmor={APPARMOR_PROFILE}"]
FIXED_SYS_MASKS = [
    "/sys/devices/virtual/powercap",
    "/sys/firmware",
]
THERMAL_THROTTLE_GLOB = "/sys/devices/system/cpu/cpu*/thermal_throttle"


class UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, socket_path: str) -> None:
        super().__init__("localhost")
        self.socket_path = socket_path

    def connect(self) -> None:
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.socket_path)


def fail(message: str) -> NoReturn:
    print(f"AURORA_KSQ_DOCKER_BUILDER_FAILURE: {message}", file=sys.stderr)
    raise SystemExit(1)


def api_request(
    method: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
    expected: tuple[int, ...] = (200,),
) -> tuple[int, bytes]:
    if not os.path.exists(DOCKER_SOCKET):
        fail(f"Docker socket is missing: {DOCKER_SOCKET}")

    body: bytes | None = None
    headers: dict[str, str] = {}
    if payload is not None:
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
        headers["Content-Length"] = str(len(body))

    conn = UnixHTTPConnection(DOCKER_SOCKET)
    try:
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        data = response.read()
    except OSError as exc:
        fail(f"Docker API {method} {path} failed: {exc}")
    finally:
        conn.close()

    if response.status not in expected:
        text = data.decode("utf-8", errors="replace")
        fail(f"Docker API {method} {path} returned HTTP {response.status}: {text}")
    return response.status, data


def json_response(method: str, path: str, *, expected: tuple[int, ...] = (200,)) -> dict[str, Any]:
    _, data = api_request(method, path, expected=expected)
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"Docker API {method} {path} returned invalid JSON: {exc}")
    if not isinstance(value, dict):
        fail(f"Docker API {method} {path} returned non-object JSON")
    return value


def engine_api_version() -> tuple[str, dict[str, Any]]:
    info = json_response("GET", "/version")
    version = info.get("ApiVersion")
    if not isinstance(version, str) or not version:
        fail("Docker /version did not return a usable ApiVersion")
    return version, info


def sys_masks() -> list[str]:
    masks = set(FIXED_SYS_MASKS)
    masks.update(glob.glob(THERMAL_THROTTLE_GLOB))
    return sorted(masks)


def parse_bind(value: str) -> str:
    parts = value.rsplit(":", 1)
    if len(parts) != 2 or parts[1] not in {"ro", "rw"}:
        fail(f"bind must end in :ro or :rw: {value!r}")
    pair, mode = parts
    paths = pair.split(":", 1)
    if len(paths) != 2:
        fail(f"bind must be SOURCE:DEST:MODE: {value!r}")
    source, dest = paths
    if not source.startswith("/") or not dest.startswith("/"):
        fail(f"bind source and destination must be absolute: {value!r}")
    if not Path(source).exists():
        fail(f"bind source does not exist: {source}")
    return f"{source}:{dest}:{mode}"


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate_host_config(inspect: dict[str, Any], expected_binds: list[str]) -> dict[str, Any]:
    host = inspect.get("HostConfig")
    if not isinstance(host, dict):
        fail("container inspect is missing HostConfig")

    if host.get("Privileged") is not False:
        fail(f"Privileged must be false, got {host.get('Privileged')!r}")
    if host.get("CapAdd") not in (None, []):
        fail(f"CapAdd must be empty, got {host.get('CapAdd')!r}")
    if host.get("NetworkMode") != "none":
        fail(f"NetworkMode must be none, got {host.get('NetworkMode')!r}")

    security_opt = host.get("SecurityOpt") or []
    if sorted(security_opt) != sorted(SECURITY_OPT):
        fail(f"unexpected SecurityOpt: {security_opt!r}")

    masked = host.get("MaskedPaths") or []
    readonly = host.get("ReadonlyPaths") or []
    if readonly:
        fail(f"ReadonlyPaths must be empty for nested procfs, got {readonly!r}")
    if any(str(path).startswith("/proc") for path in masked):
        fail(f"a /proc path remains masked: {masked!r}")

    required_masks = set(FIXED_SYS_MASKS)
    if not required_masks.issubset(set(masked)):
        fail(f"required /sys masks are missing: {masked!r}")
    if any(not str(path).startswith("/sys/") for path in masked):
        fail(f"unexpected non-/sys masked path: {masked!r}")

    actual_binds = host.get("Binds") or []
    if sorted(actual_binds) != sorted(expected_binds):
        fail(f"bind contract mismatch: expected={expected_binds!r} actual={actual_binds!r}")

    config = inspect.get("Config")
    if not isinstance(config, dict):
        fail("container inspect is missing Config")
    if config.get("Image") is None:
        fail("container inspect does not identify its image")

    return {
        "privileged": host.get("Privileged"),
        "cap_add": host.get("CapAdd"),
        "network_mode": host.get("NetworkMode"),
        "security_opt": security_opt,
        "masked_paths": masked,
        "readonly_paths": readonly,
        "binds": actual_binds,
        "config_image": config.get("Image"),
    }


def cmd_create(args: argparse.Namespace) -> None:
    if "@sha256:" not in args.image:
        fail("builder image must be pinned by sha256 digest")
    if not args.name or "/" in args.name:
        fail("container name must be a non-empty Docker name without '/'")

    binds = [parse_bind(value) for value in args.bind]
    masks = sys_masks()
    payload: dict[str, Any] = {
        "Image": args.image,
        "Cmd": ["sleep", "infinity"],
        "HostConfig": {
            "NetworkMode": "none",
            "Privileged": False,
            "SecurityOpt": SECURITY_OPT,
            "Binds": binds,
            "MaskedPaths": masks,
            "ReadonlyPaths": [],
        },
    }

    api_version, engine = engine_api_version()
    prefix = f"/v{api_version}"
    create_path = f"{prefix}/containers/create?name={quote(args.name, safe='')}"
    _, raw_create = api_request("POST", create_path, payload=payload, expected=(201,))
    try:
        created = json.loads(raw_create.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"container create returned invalid JSON: {exc}")
    if not isinstance(created, dict) or not isinstance(created.get("Id"), str) or not created["Id"]:
        fail(f"container create response has no Id: {created!r}")
    cid = created["Id"]

    evidence_dir = Path(args.evidence_dir)
    write_json(evidence_dir / "engine-version.json", engine)
    write_json(evidence_dir / "create-payload.json", payload)
    write_json(evidence_dir / "create-response.json", created)

    try:
        api_request("POST", f"{prefix}/containers/{quote(cid, safe='')}/start", expected=(204, 304))
        inspect = json_response("GET", f"{prefix}/containers/{quote(cid, safe='')}/json")
        validated = validate_host_config(inspect, binds)
        write_json(evidence_dir / "inspect.json", inspect)
        write_json(evidence_dir / "validated-contract.json", validated)
        (evidence_dir / "result.env").write_text(
            "AURORA_KSQ_DOCKER_BUILDER_CREATE=PASS\n"
            f"AURORA_KSQ_DOCKER_BUILDER_CONTAINER_ID={cid}\n",
            encoding="utf-8",
        )
    except BaseException:
        try:
            api_request("DELETE", f"{prefix}/containers/{quote(cid, safe='')}?force=true&v=true", expected=(204, 404))
        except BaseException:
            pass
        raise

    print(cid)


def cmd_remove(args: argparse.Namespace) -> None:
    api_version, _ = engine_api_version()
    prefix = f"/v{api_version}"
    api_request(
        "DELETE",
        f"{prefix}/containers/{quote(args.container, safe='')}?force=true&v=true",
        expected=(204, 404),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create the scoped SupraLINUX KSQ Docker builder. Docker's CLI can only disable all "
            "system-path protection with systempaths=unconfined; this helper uses the stable Engine "
            "API to remove only /proc overlays required by nested sbuild procfs while retaining the "
            "current Moby /sys masks."
        )
    )
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="create, start and validate a KSQ builder container")
    create.add_argument("--image", required=True)
    create.add_argument("--name", required=True)
    create.add_argument("--bind", action="append", default=[], metavar="SOURCE:DEST:MODE")
    create.add_argument("--evidence-dir", required=True)
    create.set_defaults(func=cmd_create)

    remove = sub.add_parser("remove", help="force-remove a KSQ builder container")
    remove.add_argument("container")
    remove.set_defaults(func=cmd_remove)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
