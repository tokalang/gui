#!/usr/bin/env python3
"""Qualify official/gui through a locked standalone macOS package consumer."""

from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile


PACKAGE = Path(__file__).resolve().parents[1]
UNICODE_VERSION = "0.1.1"
UNICODE_ARCHIVE_SHA256 = "c68569e6efbd9eb9bf85226eca68de3a0187d4300e320aeb13857be73b5ad28a"
UNICODE_CONTENT_SHA256 = "8c82ff393812d1ddd9a8b1f6d71d8ab49863a68b6193af1d784ea722e052fe76"


class QualificationError(RuntimeError):
    pass


def run(argv: list[str], *, cwd: Path,
        env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        argv, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, timeout=180,
    )
    if result.returncode != 0:
        raise QualificationError(
            "command failed (%d): %s\nstdout:\n%s\nstderr:\n%s"
            % (result.returncode, " ".join(argv), result.stdout, result.stderr)
        )
    return result


def expect_failure(argv: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    result = subprocess.run(
        argv, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, timeout=180,
    )
    if result.returncode == 0:
        raise QualificationError("expected command to fail: " + " ".join(argv))


def resolve_toolchain(env: dict[str, str]) -> tuple[Path, Path, Path, Path]:
    root_is_set = "TOKA_ROOT" in env
    explicit_keys = ("TOKA", "TOKAC", "TOKA_LIB")
    explicit_set = [key for key in explicit_keys if key in env]
    if root_is_set and explicit_set:
        raise QualificationError("set either TOKA_ROOT or TOKA/TOKAC/TOKA_LIB, not both")
    if root_is_set:
        if not env["TOKA_ROOT"].strip():
            raise QualificationError("TOKA_ROOT must not be empty")
        root = Path(env["TOKA_ROOT"]).expanduser().resolve()
        toka = root / "build" / "bin" / "toka"
        tokac = root / "build" / "bin" / "tokac"
        library = root / "lib"
        build_driver = root / "tools" / "scripts" / "toka_build.py"
        package_helper = root / "lib" / "toolchain" / "toka_package.py"
    else:
        if len(explicit_set) != len(explicit_keys):
            missing = ", ".join(key for key in explicit_keys if key not in env)
            raise QualificationError(
                "set TOKA_ROOT or all of TOKA/TOKAC/TOKA_LIB"
                + (" (missing: " + missing + ")" if missing else "")
            )
        empty = [key for key in explicit_keys if not env[key].strip()]
        if empty:
            raise QualificationError("toolchain variables must not be empty: " + ", ".join(empty))
        toka = Path(env["TOKA"]).expanduser().resolve()
        tokac = Path(env["TOKAC"]).expanduser().resolve()
        library = Path(env["TOKA_LIB"]).expanduser().resolve()
        build_driver = library / "toolchain" / "toka_build.py"
        package_helper = library / "toolchain" / "toka_package.py"
    required = {
        "toka": toka,
        "tokac": tokac,
        "toka_rt.o": library / "sys" / "toka_rt.o",
        "toka_build.py": build_driver,
        "toka_package.py": package_helper,
    }
    missing_files = [name for name, path in required.items() if not path.is_file()]
    if not library.is_dir():
        missing_files.append("TOKA_LIB")
    if missing_files:
        raise QualificationError("incomplete Toka toolchain (missing: %s)" % ", ".join(missing_files))
    return toka, tokac, library, build_driver


def make_sdk(work: Path, source_library: Path, build_driver: Path) -> Path:
    library = work / "sdk" / "lib"
    shutil.copytree(
        source_library, library,
        ignore=shutil.ignore_patterns("*.pyc", "__pycache__"),
    )
    toolchain = library / "toolchain"
    toolchain.mkdir(parents=True, exist_ok=True)
    shutil.copy2(build_driver, toolchain / "toka_build.py")
    return library


def tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    records: list[tuple[str, Path]] = []
    for directory, names, files in os.walk(root, topdown=True, followlinks=False):
        directory_path = Path(directory)
        names[:] = sorted(
            name for name in names
            if not (directory_path == root and name in (".git", ".toka"))
        )
        for name in names:
            if (directory_path / name).is_symlink():
                raise QualificationError("package contains a symbolic link")
        for name in sorted(files):
            path = directory_path / name
            relative = path.relative_to(root).as_posix()
            if relative == "package.lock":
                continue
            if path.is_symlink() or not path.is_file():
                raise QualificationError("package contains a non-regular file: " + relative)
            records.append((relative, path))
    for relative, path in sorted(records):
        encoded = relative.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
        digest.update(path.stat().st_size.to_bytes(8, "big"))
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def write_consumer(project: Path, dependency: Path, source: Path) -> None:
    (project / "src").mkdir(parents=True)
    (project / "package.tk").write_text(
        "pub const PACKAGE = (\n"
        '    name = "gui_consumer",\n'
        '    version = "0.1.0",\n'
        "    dependencies = (\n"
        "        gui = %s,\n"
        "    )\n"
        ")\n" % json.dumps(str(dependency)),
        encoding="utf-8",
    )
    (project / "build.tk").write_text(
        "import build::{Executable, run_build}\n\n"
        "fn main() -> i32 {\n"
        '    auto app# = Executable::make(c"gui_consumer", c"src/main.tk")\n'
        "    return run_build(app)\n"
        "}\n",
        encoding="utf-8",
    )
    shutil.copy2(source, project / "src" / "main.tk")
    (project / "src" / "fixture.png").write_bytes(base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl6SgAAAABJRU5ErkJggg=="
    ))
    (project / "src" / "fixture.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
        '<path fill="#52d273" d="M2 2h12v12H2z"/>'
        "</svg>", encoding="utf-8",
    )


def verify_exact_lock(locked: bytes, dependency: Path) -> None:
    lines = locked.decode("utf-8").splitlines()
    if len(lines) != 3 or lines[0] != "toka-lock-v1":
        raise QualificationError("online fetch did not produce an exact two-package v1 lock")
    gui = lines[1].split("\t")
    unicode = lines[2].split("\t")
    resolved_dependency = str(dependency.resolve())
    expected_gui = ["package", "gui", "path", resolved_dependency, resolved_dependency, "-"]
    if (len(gui) != 8 or gui[:6] != expected_gui or
            gui[6] != tree_sha256(dependency) or gui[7] != "unicode"):
        raise QualificationError("online fetch produced an invalid GUI path lock:\n" + lines[1])
    expected_unicode = [
        "package", "unicode", "registry", "unicode", UNICODE_VERSION,
        UNICODE_ARCHIVE_SHA256, UNICODE_CONTENT_SHA256, "-",
    ]
    if unicode != expected_unicode:
        raise QualificationError("online fetch did not produce the exact Unicode registry lock:\n" + lines[2])


def assert_native_object(project: Path) -> None:
    native = list((project / ".toka" / "build" / "native").glob("toka_gui-*.o"))
    if not native:
        raise QualificationError("toka build did not rebuild the GUI native object")


def assert_framework_linkage(program: Path, env: dict[str, str]) -> None:
    result = run(["otool", "-L", str(program)], cwd=program.parent, env=env)
    for framework in ("AppKit.framework", "Metal.framework", "QuartzCore.framework"):
        if framework not in result.stdout:
            raise QualificationError("GUI consumer did not link " + framework)


def compile_appkit_smoke(work: Path, env: dict[str, str]) -> None:
    compiler = env.get("CC") or run(["xcrun", "--find", "clang"], cwd=PACKAGE, env=env).stdout.strip()
    sdk = run(["xcrun", "--show-sdk-path"], cwd=PACKAGE, env=env).stdout.strip()
    program = work / "appkit_smoke"
    run([compiler, "-Wall", "-Wextra", "-Werror", "-isysroot", sdk,
         str(PACKAGE / "tests" / "appkit_smoke.m"),
         "-framework", "AppKit", "-framework", "Metal", "-framework", "QuartzCore",
         "-o", str(program)], cwd=PACKAGE, env=env)
    run([str(program)], cwd=PACKAGE, env=env)


def main() -> int:
    if platform.system() != "Darwin":
        raise QualificationError("official/gui qualification requires macOS")
    manifest = (PACKAGE / "package.tk").read_text(encoding="utf-8")
    for required in ('version = "0.1.0"', 'compiler = "1.0.0-rc.4"',
                     'unicode = "unicode:0.1.1"'):
        if required not in manifest:
            raise QualificationError("package manifest is missing: " + required)
    host_env = dict(os.environ)
    toka, tokac, source_library, build_driver = resolve_toolchain(host_env)

    with tempfile.TemporaryDirectory(prefix="toka-gui-package-") as temporary:
        work = Path(temporary)
        sdk = make_sdk(work, source_library, build_driver)
        base_env = dict(host_env)
        base_env.update({"TOKAC": str(tokac), "TOKA_LIB": str(sdk)})
        base_env["TOKA_REGISTRY_URL"] = "https://pkg.tokalang.dev"
        base_env.pop("TOKA_ROOT", None)
        base_env.pop("TOKA", None)
        base_env.pop("TOKA_OFFLINE", None)
        dependency = work / "gui"
        shutil.copytree(
            PACKAGE, dependency,
            ignore=shutil.ignore_patterns(".git", ".toka", "target", "__pycache__", "*.pyc"),
        )
        consumer = work / "consumer"
        write_consumer(consumer, dependency, dependency / "tests" / "smoke.tk")

        run([str(toka), "fetch"], cwd=consumer, env=base_env)
        lock = consumer / "package.lock"
        locked = lock.read_bytes()
        verify_exact_lock(locked, dependency)
        archive = consumer / ".toka" / "cache" / "archives" / (UNICODE_ARCHIVE_SHA256 + ".tar.gz")
        if not archive.is_file() or hashlib.sha256(archive.read_bytes()).hexdigest() != UNICODE_ARCHIVE_SHA256:
            raise QualificationError("online fetch did not cache the exact Unicode archive")
        cached_archives = sorted(
            path for path in archive.parent.iterdir() if path.is_file()
        )
        if cached_archives != [archive]:
            raise QualificationError("fresh online resolve cached unexpected package archives")

        unicode = consumer / ".toka" / "packages" / ("unicode-" + UNICODE_VERSION)
        includes = [str(sdk), str(unicode / "lib"), str(dependency / "lib")]
        check_prefix = [str(tokac)]
        for include in includes:
            check_prefix.extend(["-I", include])
        for rejected in ("window_clone_rejected.tk", "window_thread_spawn_rejected.tk",
                         "app_thread_spawn_rejected.tk"):
            expect_failure([*check_prefix, "--check-only", str(dependency / "tests" / rejected)],
                           cwd=consumer, env=base_env)
        for accepted in (dependency / "tests" / "host_event_source_compile.tk",
                         dependency / "examples" / "settings.tk"):
            run([*check_prefix, "--check-only", str(accepted)], cwd=consumer, env=base_env)
        grapheme = work / "grapheme_selection"
        run([*check_prefix, str(dependency / "tests" / "grapheme_selection.tk"),
             "-o", str(grapheme)], cwd=consumer, env=base_env)
        run([str(grapheme)], cwd=consumer, env=base_env)

        run([str(toka), "build"], cwd=consumer, env=base_env)
        program = consumer / "target" / "debug" / "gui_consumer"
        if not program.is_file():
            raise QualificationError("toka build did not produce the GUI consumer")
        assert_native_object(consumer)
        assert_framework_linkage(program, base_env)
        compile_appkit_smoke(work, base_env)
        if base_env.get("TOKA_GUI_DESKTOP_SMOKE") == "1":
            run([str(program)], cwd=consumer, env=base_env)

        preserved_archive = work / archive.name
        shutil.copy2(archive, preserved_archive)
        shutil.rmtree(consumer / "target")
        shutil.rmtree(consumer / ".toka")
        (consumer / ".toka_build_exe").unlink(missing_ok=True)
        offline_archives = consumer / ".toka" / "cache" / "archives"
        offline_archives.mkdir(parents=True)
        shutil.copy2(preserved_archive, offline_archives / archive.name)
        if (consumer / "target").exists() or (consumer / ".toka" / "packages").exists() or \
                (consumer / ".toka" / "build").exists() or (consumer / ".toka_build_exe").exists():
            raise QualificationError("offline replay retained unpacked packages or build output")
        offline_files = sorted(
            path.relative_to(consumer / ".toka").as_posix()
            for path in (consumer / ".toka").rglob("*") if path.is_file()
        )
        if offline_files != ["cache/archives/" + archive.name]:
            raise QualificationError("offline replay state contains files beyond the locked Unicode archive")
        offline = dict(base_env)
        offline["TOKA_OFFLINE"] = "1"
        run([str(toka), "fetch"], cwd=consumer, env=offline)
        if lock.read_bytes() != locked:
            raise QualificationError("offline Unicode replay changed package.lock")
        if not (consumer / ".toka" / "packages" / ("unicode-" + UNICODE_VERSION)).is_dir():
            raise QualificationError("offline replay did not unpack Unicode from the cached archive")
        run([str(toka), "build"], cwd=consumer, env=offline)
        if lock.read_bytes() != locked:
            raise QualificationError("offline GUI build changed package.lock")
        assert_native_object(consumer)
        assert_framework_linkage(program, offline)

        shutil.copy2(dependency / "tests" / "image_smoke_template.tk", consumer / "src" / "main.tk")
        shutil.rmtree(consumer / "target")
        shutil.rmtree(consumer / ".toka" / "build")
        (consumer / ".toka_build_exe").unlink(missing_ok=True)
        run([str(toka), "build"], cwd=consumer, env=offline)
        assert_native_object(consumer)
        assert_framework_linkage(program, offline)
        if offline.get("TOKA_GUI_DESKTOP_SMOKE") == "1":
            run([str(program)], cwd=consumer, env=offline)
        else:
            print("desktop Metal smoke not requested; compile/link/framework gates passed")

    print(json.dumps({
        "result": "pass",
        "schema": "toka.official-gui-package-v1",
        "stages": {
            "strict_toolchain": "pass",
            "exact_unicode_registry_lock": "pass",
            "strict_archive_only_offline_replay": "pass",
            "ownership_and_thread_affinity": "pass",
            "grapheme_editor": "pass",
            "native_rebuild": "pass",
            "appkit_framework_smoke": "pass",
            "gui_program_compile_and_link": "pass",
            "desktop_metal_smoke": "pass" if host_env.get("TOKA_GUI_DESKTOP_SMOKE") == "1" else "not-requested",
        },
        "version": 1,
    }, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, QualificationError, subprocess.TimeoutExpired) as error:
        print("FAIL: " + str(error))
        raise SystemExit(1)
