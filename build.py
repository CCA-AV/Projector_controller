#!/usr/bin/env python3
"""Build the Projector Controller distributables."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DIST_ROOT = ROOT / "dist"
DIST_MAIN = DIST_ROOT / "main"
PROJECTORS_DIR = ROOT / "projectors"
IMAGES_DIR = ROOT / "images"
ICON_FILE = IMAGES_DIR / "icon.ico"
UPDATER_DIR = ROOT / "updater"
VERSION_FILE = ROOT / "version"
WINDOWS_ZIP = ROOT / "windows.zip"
WINDOWS_AUTO_ZIP = ROOT / "windows_autoupdating.zip"
UPDATER_FILES = ("data.json", "Projector_Control.exe")


def run_pyinstaller() -> None:
    if not ICON_FILE.exists():
        raise FileNotFoundError(f"Missing application icon: {ICON_FILE}")
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "main.py",
        "--windowed",
        "--noconfirm",
        "--hidden-import=nebulatk",
        "--additional-hooks-dir=.",
        f"--icon={ICON_FILE}",
    ]
    print(f"[build] Running PyInstaller: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=ROOT, check=True)


def copy_tree(src: Path, dest: Path) -> None:
    if not src.exists():
        raise FileNotFoundError(f"Missing required directory: {src}")
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def ensure_dist_main() -> None:
    if not DIST_MAIN.exists():
        raise FileNotFoundError("dist/main was not produced. Did PyInstaller finish?")


def stage_runtime_assets() -> None:
    print("[build] Copying runtime resources into dist/main")
    internal_projectors = DIST_MAIN / "_internal" / "projectors"
    internal_projectors.parent.mkdir(parents=True, exist_ok=True)
    copy_tree(PROJECTORS_DIR, internal_projectors)
    copy_tree(IMAGES_DIR, DIST_MAIN / "images")


def read_version() -> str:
    if version := VERSION_FILE.read_text(encoding="utf-8").strip():
        return version
    raise ValueError("Version file is empty.")


def zip_directory(source_dir: Path, destination: Path) -> None:
    if not source_dir.exists():
        raise FileNotFoundError(f"Cannot zip missing folder: {source_dir}")
    if destination.exists():
        destination.unlink()

    print(f"[build] Creating {destination.name}")
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*")):
            relative_path = path.relative_to(source_dir)
            if path.is_dir():
                if not any(path.iterdir()):
                    archive.writestr(f"{relative_path}/", "")
                continue
            archive.write(path, relative_path)


def create_standard_zip() -> None:
    zip_directory(DIST_MAIN, WINDOWS_ZIP)


def create_autoupdate_zip(version: str) -> None:
    if missing := [name for name in UPDATER_FILES if not (UPDATER_DIR / name).exists()]:
        raise FileNotFoundError(
            f"Updater files not found: {', '.join(missing)} (expected inside {UPDATER_DIR})"
        )

    with tempfile.TemporaryDirectory() as staging_dir:
        staging_root = Path(staging_dir)
        versions_target = staging_root / "versions" / f"projector-controller-{version}"
        versions_target.parent.mkdir(parents=True, exist_ok=True)
        copy_tree(DIST_MAIN, versions_target)
        for file_name in UPDATER_FILES:
            shutil.copy2(UPDATER_DIR / file_name, staging_root / file_name)
        write_state_file(staging_root, version)
        zip_directory(staging_root, WINDOWS_AUTO_ZIP)


def write_state_file(staging_root: Path, version: str) -> None:
    state_path = staging_root / "state.json"
    payload = {
        "version": version,
        "path": f"versions\\projector-controller-{version}",
    }
    state_path.write_text(json.dumps(payload), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build PyInstaller output and accompanying zip archives."
    )
    parser.add_argument(
        "--skip-pyinstaller",
        action="store_true",
        help="Reuse the existing dist/ folder instead of invoking PyInstaller.",
    )
    return parser.parse_args()


def perform_build(skip_pyinstaller: bool) -> None:
    if skip_pyinstaller:
        print("[build] Skipping PyInstaller step (requested)")
    else:
        run_pyinstaller()
    ensure_dist_main()
    stage_runtime_assets()
    create_standard_zip()
    version = read_version()
    create_autoupdate_zip(version)


def main() -> None:
    args = parse_args()
    try:
        perform_build(args.skip_pyinstaller)
        print("[build] Done")
    except Exception as exc:  # pragma: no cover - build scripts are not unit tested
        print(f"[build] Failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
