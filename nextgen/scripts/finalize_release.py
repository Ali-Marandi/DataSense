from __future__ import annotations

import argparse
import hashlib
import json
import shutil
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize a signed DataSense Windows release.")
    parser.add_argument("--version", required=True)
    parser.add_argument("--installer", type=Path)
    args = parser.parse_args()

    bundle = DIST / APP_NAME
    executable = bundle / f"{APP_NAME}.exe"
    if not executable.exists():
        raise SystemExit(f"Missing Windows executable: {executable}")
    # Any portable archive produced before signing is unsafe to publish.
    for stale in DIST.glob(f"DataSense-{args.version}-*-portable.zip"):
        stale.unlink()
    portable_zip = Path(shutil.make_archive(str(DIST / f"DataSense-{args.version}-windows-x64-portable"), "zip", root_dir=bundle))

    assets: dict[str, dict[str, int | str]] = {}
    for asset in (executable, portable_zip):
        assets[asset.name] = {"sha256": sha256(asset), "bytes": asset.stat().st_size}
    if args.installer:
        installer = args.installer.resolve()
        if not installer.exists():
            raise SystemExit(f"Missing installer: {installer}")
        shutil.copy2(installer, DIST / installer.name)
        copied_installer = DIST / installer.name
        assets[copied_installer.name] = {"sha256": sha256(copied_installer), "bytes": copied_installer.stat().st_size}

    sbom = DIST / "sbom-python.json"
    if not sbom.exists():
        raise SystemExit("Missing Python SBOM. Run build_release.py before finalizing.")
    assets[sbom.name] = {"sha256": sha256(sbom), "bytes": sbom.stat().st_size}
    manifest = {
        "schema": "datasense.release-manifest/v1",
        "app_name": APP_NAME,
        "version": args.version,
        "platform": "windows-x64",
        "assets": assets,
    }
    manifest_path = DIST / "release-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    assets[manifest_path.name] = {"sha256": sha256(manifest_path), "bytes": manifest_path.stat().st_size}
    checksums = DIST / "SHA256SUMS.txt"
    checksums.write_text("\n".join(f"{meta['sha256']}  {name}" for name, meta in sorted(assets.items())) + "\n", encoding="utf-8")
    print(f"Finalized {len(assets)} release assets in {DIST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
