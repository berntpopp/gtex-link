"""The deployed Compose file must satisfy the fleet controller's projection contract.

`docker/docker-compose.npm.yml` is the only file the GeneFoundry controller deploys
(its `projects.yaml` entry names it as the single `compose_file`). Before it will author
a deployment record the controller renders that file with
`docker compose config --format json`, projects it and refuses anything that does not
declare the full security field set -- so a field dropped from this file is not a style
regression, it is an undeployable service.

These guards mirror `scripts/utils/deployment_preflight.py` in the private controller
repo. They are deliberately literal about the *shape* the renderer produces, because two
of the rules are counter-intuitive:

* `volumes: []` does not satisfy the required-field check. compose-go tags the field
  `omitempty`, so an empty list is dropped from `docker compose config` output and the
  rendered service has no `volumes` key at all.
* a fractional `deploy.resources.limits.cpus` renders as a JSON float, and the
  projection accepts only string/integer limits.

The deploy contract also *contradicts* the shared release contract, so the two must not be
mixed: `container_release.py validate-compose` forbids `user` on the application service of
the Compose files named in `container-release.json`. The numeric user therefore belongs in
the deployed npm overlay only, and a guard below keeps it out of the release stack.

Research use only; not clinical decision support.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]  # tests/unit/<file> -> repo root
NPM_COMPOSE = ROOT / "docker" / "docker-compose.npm.yml"
PROD_COMPOSE = ROOT / "docker" / "docker-compose.prod.yml"
DOCKERFILE = ROOT / "docker" / "Dockerfile"
RELEASE_MANIFEST = ROOT / "container-release.json"

# scripts/utils/deployment_preflight.py::_APP_REQUIRED
APP_REQUIRED = frozenset(
    {
        "image",
        "read_only",
        "cap_drop",
        "security_opt",
        "restart",
        "networks",
        "volumes",
        "user",
    }
)
# The same module's user pattern, and `runtime_observer._verify_runtime_settings`,
# which rejects a user that is not a positive integer (the image's `USER app`
# inspects as the name "app").
NUMERIC_USER = re.compile(r"[1-9][0-9]*(?::[1-9][0-9]*)?")


def _npm_services() -> dict[str, dict[str, Any]]:
    return yaml.safe_load(NPM_COMPOSE.read_text(encoding="utf-8"))["services"]


def _image_uid_gid() -> tuple[str, str]:
    """Return the uid:gid the image actually runs as, read from the Dockerfile.

    The fleet is NOT uniform -- sibling `-link` images that use `useradd --system`
    run as 999 -- so this is derived per repo instead of hard-coded.
    """
    text = DOCKERFILE.read_text(encoding="utf-8")
    gid = re.search(r"groupadd --gid (\d+)", text)
    uid = re.search(r"useradd --uid (\d+)", text)
    assert gid and uid, "Dockerfile must create the runtime account with explicit ids"
    assert re.search(r"^USER app$", text, re.MULTILINE), "Dockerfile must drop to that account"
    return uid.group(1), gid.group(1)


def test_deployed_compose_declares_every_required_projection_field() -> None:
    """Each service carries the controller's full required field set."""
    for name, service in _npm_services().items():
        missing = APP_REQUIRED - set(service)
        assert not missing, (
            f"{name} is missing {sorted(missing)}; the controller's canonical projection "
            "refuses to author a deployment record without them "
            "(scripts/utils/deployment_preflight.py::_APP_REQUIRED)"
        )


def test_declared_user_is_numeric_and_matches_the_image() -> None:
    """The declared user is numeric and is this image's real uid:gid."""
    uid, gid = _image_uid_gid()
    for name, service in _npm_services().items():
        user = service["user"]
        assert isinstance(user, str) and NUMERIC_USER.fullmatch(user), (
            f"{name} declares user={user!r}; it must be numeric -- the runtime observer "
            "rejects a user name, and `USER app` inspects as 'app'"
        )
        assert user == f"{uid}:{gid}", (
            f"{name} declares user={user!r} but the image runs as {uid}:{gid} "
            "(docker/Dockerfile). Never copy this value from a sibling repo: the fleet "
            "runs a mix of uid 999 and uid 10001."
        )


def test_declared_volumes_are_named_and_hold_no_persistent_state() -> None:
    """`volumes` is satisfied without giving a data-less service durable storage.

    The required `volumes` key cannot be satisfied by an empty list (it is dropped by
    the renderer), and this service declares `data.mode: "none"`, so every mount it
    declares must be RAM-backed rather than a real disk volume.
    """
    assert json.loads(RELEASE_MANIFEST.read_text(encoding="utf-8"))["data"]["mode"] == "none", (
        "this guard assumes gtex-link stores nothing; revisit it if that changes"
    )
    compose = yaml.safe_load(NPM_COMPOSE.read_text(encoding="utf-8"))
    declared = compose.get("volumes") or {}
    for name, service in compose["services"].items():
        mounts = service["volumes"]
        assert isinstance(mounts, list) and mounts, (
            f"{name} declares no volumes; an empty list is dropped by "
            "`docker compose config` and fails the required-field check"
        )
        for mount in mounts:
            assert isinstance(mount, str), f"{name} mount {mount!r} must be short-form named"
            source, _, target = mount.partition(":")
            assert source in declared, f"{name} mounts undeclared volume {source!r}"
            assert target.startswith("/"), f"{name} mount {mount!r} must target an absolute path"
            options = declared[source].get("driver_opts") or {}
            assert options.get("type") == "tmpfs", (
                f"{source} is disk-backed; a service that declares data.mode 'none' must "
                "not grow persistent state to satisfy a shape check"
            )
            assert "noexec" in options.get("o", ""), f"{source} must stay noexec"
            assert "nosuid" in options.get("o", ""), f"{source} must stay nosuid"


def test_cpu_limit_stays_an_integer() -> None:
    """A fractional cpus value renders as a float and the projection rejects it."""
    for name, service in _npm_services().items():
        limits = service["deploy"]["resources"]["limits"]
        assert isinstance(limits["cpus"], int), (
            f"{name} declares cpus={limits['cpus']!r}; Compose renders a fractional or "
            "interpolated value as a JSON float, and the projection accepts only "
            "string/integer resource limits"
        )


def test_expose_declares_the_protocol() -> None:
    """`expose: 8000/tcp` keeps ExposedPorts a single key the observer can match.

    Without the suffix the container inspects with both `8000` and `8000/tcp` (the
    unsuffixed key comes from Compose, the other from the image's EXPOSE), and the
    runtime observer compares the set exactly.
    """
    for name, service in _npm_services().items():
        for port in service["expose"]:
            assert str(port).endswith(("/tcp", "/udp")), (
                f"{name} exposes {port!r} without a protocol suffix"
            )


def test_hardening_controls_are_not_weakened() -> None:
    """The controls the projection also checks stay exactly as reviewed."""
    for name, service in _npm_services().items():
        assert service["read_only"] is True, f"{name} lost its read-only root filesystem"
        assert service["cap_drop"] == ["ALL"], f"{name} must drop exactly ALL capabilities"
        assert service["security_opt"] == ["no-new-privileges:true"], (
            f"{name} must keep no-new-privileges and add no weakening option"
        )
        assert service["restart"] == "unless-stopped", f"{name} has an unreviewed restart policy"
        assert service["init"] is True, f"{name} lost its init process"
        assert service["pids_limit"] == 256, f"{name} lost its pids limit"
        # S108: an in-container tmpfs target, not a host temporary path.
        tmpdir = "/tmp/gtex-link"  # noqa: S108
        assert any(tmpdir in entry for entry in service["tmpfs"]), (
            f"{name} lost the writable tmpfs its TMPDIR points at"
        )
        assert "ports" not in service, f"{name} publishes ports; the projection forbids it"
        assert "build" not in service, f"{name} builds; deploys pull the attested image"


def test_release_compose_files_never_declare_a_user() -> None:
    """The shared release gate forbids on the release stack what the deploy file requires.

    `container_release.py validate-compose` (genefoundry-router,
    `genefoundry_router/release/compose.py`) rejects a rendered application service that
    carries `user` -- twice over: "user override must be absent", and `user` is not in its
    `ALLOWED_SERVICE_KEYS`, so it is also an "unapproved rendered field". The deployment
    controller requires the exact opposite, so the numeric user must live only in the npm
    overlay, which the release gate never reads. Adding it to a file listed in
    `container-release.json` fails Container CI, and on a tag a failed release burns a
    version.

    Read as text, not YAML: these files use Compose's `!reset`/`!override` tags, which
    `yaml.safe_load` cannot construct.
    """
    manifest = json.loads(RELEASE_MANIFEST.read_text(encoding="utf-8"))
    for name in manifest["service"]["compose_files"]:
        text = (ROOT / name).read_text(encoding="utf-8")
        assert not re.search(r"^\s+user:", text, re.MULTILINE), (
            f"{name} is part of the release stack (container-release.json) and must not "
            "declare `user`; the shared release gate rejects it"
        )
    assert PROD_COMPOSE.name in {Path(name).name for name in manifest["service"]["compose_files"]}
