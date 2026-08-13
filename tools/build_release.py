#!/usr/bin/env python3
"""Build the deterministic official/gui 0.1.0 release archive."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tarfile
import tempfile


ROOT = Path(__file__).resolve().parents[1]
RELEASE_FILES = (
    "package.tk",
    "README.md",
    "LICENSE",
    "lib/official/gui.tk",
    "lib/official/gui/text.tk",
    "native/toka_gui.m",
    "examples/settings.tk",
    "tests/app_thread_spawn_rejected.tk",
    "tests/appkit_smoke.m",
    "tests/grapheme_selection.tk",
    "tests/host_event_source_compile.tk",
    "tests/image_smoke_template.tk",
    "tests/qualify_package.py",
    "tests/smoke.tk",
    "tests/window_clone_rejected.tk",
    "tests/window_thread_spawn_rejected.tk",
    "tools/build_release.py",
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def content_sha256() -> str:
    digest = hashlib.sha256()
    for relative in sorted(RELEASE_FILES):
        path = ROOT / relative
        encoded = relative.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
        digest.update(path.stat().st_size.to_bytes(8, "big"))
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def validate_source() -> None:
    missing = [relative for relative in RELEASE_FILES if not (ROOT / relative).is_file()]
    if missing:
        raise RuntimeError("release allowlist is missing files: " + ", ".join(missing))
    manifest = (ROOT / "package.tk").read_text(encoding="utf-8")
    for required in ('version = "0.1.0"', 'compiler = "1.0.0-rc.4"',
                     'unicode = "unicode:0.1.1"'):
        if required not in manifest:
            raise RuntimeError("package manifest is missing: " + required)
    apple_double = sorted(path.relative_to(ROOT).as_posix() for path in ROOT.rglob("._*"))
    if apple_double:
        raise RuntimeError("package contains AppleDouble metadata: " + ", ".join(apple_double))


def write_archive(path: Path, source_date_epoch: int) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=source_date_epoch) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as archive:
                for relative in RELEASE_FILES:
                    source_path = ROOT / relative
                    info = tarfile.TarInfo(relative)
                    info.size = source_path.stat().st_size
                    info.mode = 0o755 if relative.endswith(".py") else 0o644
                    info.mtime = source_date_epoch
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    with source_path.open("rb") as source:
                        archive.addfile(info, source)


def validate_archive(path: Path, source_date_epoch: int) -> None:
    with tarfile.open(path, "r:gz") as archive:
        members = archive.getmembers()
    if [member.name for member in members] != list(RELEASE_FILES):
        raise RuntimeError("release archive member list does not match the exact allowlist")
    for member in members:
        parts = PurePosixPath(member.name).parts
        expected_mode = 0o755 if member.name.endswith(".py") else 0o644
        if (not member.isfile() or member.name.startswith("/") or ".." in parts or
                any(part.startswith("._") for part in parts)):
            raise RuntimeError("unsafe release archive member: " + member.name)
        if (member.uid, member.gid, member.uname, member.gname, member.mtime,
                member.mode) != (0, 0, "", "", source_date_epoch, expected_mode):
            raise RuntimeError("non-deterministic release metadata: " + member.name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-date-epoch", type=int, default=0)
    arguments = parser.parse_args()
    if arguments.source_date_epoch < 0:
        raise RuntimeError("source date epoch must not be negative")
    validate_source()
    output = arguments.output.resolve()
    if not output.parent.is_dir():
        raise RuntimeError("output directory does not exist: " + str(output.parent))
    descriptor, temporary_name = tempfile.mkstemp(
        prefix="." + output.name + ".", suffix=".tmp", dir=output.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        write_archive(temporary, arguments.source_date_epoch)
        validate_archive(temporary, arguments.source_date_epoch)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    print(json.dumps({
        "archive": str(output),
        "archive_sha256": file_sha256(output),
        "content_sha256": content_sha256(),
        "members": list(RELEASE_FILES),
        "source_date_epoch": arguments.source_date_epoch,
    }, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
