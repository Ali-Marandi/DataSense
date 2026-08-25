from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
APP_NAME = "DataSense"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_version() -> str:
    import tomllib

    payload = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(payload["project"]["version"])


def run(command: list[str]) -> None:
    completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode:
        raise SystemExit(completed.returncode)


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


def build(version: str, *, skip_tests: bool = False) -> dict[str, Path]:
    if not skip_tests:
        run([sys.executable, "-m", "pytest"])
    shutil.rmtree(DIST, ignore_errors=True)
    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--windowed",
            "--name",
            APP_NAME,
            "--collect-all",
            "PyQt6",
            "--collect-all",
            "platformdirs",
            "--collect-all",
            "pandas",
            "--collect-all",
            "pyarrow",
            "main.py",
        ]
    )
    bundle = DIST / APP_NAME
    executable = bundle / (f"{APP_NAME}.exe" if sys.platform == "win32" else APP_NAME)
    if not executable.exists():
        raise RuntimeError(f"Expected executable was not created: {executable}")

    portable_base = DIST / f"DataSense-{version}-{sys.platform}-portable"
    portable_zip = Path(shutil.make_archive(str(portable_base), "zip", root_dir=bundle))
    manifest = {
        "schema": "datasense.release-manifest/v1",
        "app_name": APP_NAME,
        "version": version,
        "platform": sys.platform,
        "bundle_executable": executable.name,
        "assets": {
            executable.name: {"sha256": sha256(executable), "bytes": executable.stat().st_size},
            portable_zip.name: {"sha256": sha256(portable_zip), "bytes": portable_zip.stat().st_size},
        },
    }
    manifest_path = DIST / "release-manifest.json"
    write_text(manifest_path, json.dumps(manifest, indent=2, sort_keys=True))
    sbom_path = DIST / "sbom-python.json"
    packages = subprocess.check_output([sys.executable, "-m", "pip", "list", "--format=json"], text=True)
    write_text(sbom_path, packages)
    checksum_path = DIST / "SHA256SUMS.txt"
    write_text(
        checksum_path,
        "\n".join(
            f"{sha256(path)}  {path.name}" for path in (executable, portable_zip, manifest_path, sbom_path)
        )
        + "\n",
    )
    return {
        "bundle": bundle,
        "executable": executable,
        "portable_zip": portable_zip,
        "manifest": manifest_path,
        "sbom": sbom_path,
        "checksums": checksum_path,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a deterministic local DataSense release bundle.")
    parser.add_argument("--version", default=project_version())
    parser.add_argument("--skip-tests", action="store_true")
    args = parser.parse_args()
    assets = build(args.version, skip_tests=args.skip_tests)
    for name, path in assets.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
