import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import sysconfig
from datetime import datetime
from pathlib import Path


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd, cwd=None):
    subprocess.check_call(cmd, cwd=cwd)


def build_extensions(root_dir):
    run([sys.executable, "setup.py", "build_ext", "--inplace"], cwd=root_dir)


def copy_tree(src, dst):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def build_dist(root_dir, dist_dir):
    firestorm_dir = root_dir / "FireStorm"
    modules_dir = firestorm_dir / "modules"
    if not firestorm_dir.exists():
        raise SystemExit("FireStorm directory not found")

    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True, exist_ok=True)

    # Core entrypoints at root (same layout as update_v2.zip)
    for entry in ["FireStorm.py", "uploader.py", "update_installer.py", "ver"]:
        src = firestorm_dir / entry
        if src.exists():
            if src.is_dir():
                shutil.copytree(src, dist_dir / entry)
            else:
                shutil.copy2(src, dist_dir / entry)

    # Resources
    for resource in ["settings", "layouts", "img"]:
        src = firestorm_dir / resource
        if src.exists():
            shutil.copytree(src, dist_dir / resource)

    # Modules: keep __init__.py, compiled extensions only
    dst_modules = dist_dir / "modules"
    dst_modules.mkdir()
    init_file = modules_dir / "__init__.py"
    if init_file.exists():
        shutil.copy2(init_file, dst_modules / "__init__.py")

    ext_suffix = sysconfig.get_config_var("EXT_SUFFIX") or ".so"
    for path in modules_dir.glob(f"*{ext_suffix}"):
        shutil.copy2(path, dst_modules / path.name)



def write_manifest(dist_dir, version):
    manifest = {
        "version": version,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "files": {},
    }
    for root, _, files in os.walk(dist_dir):
        for name in files:
            file_path = Path(root) / name
            rel = file_path.relative_to(dist_dir).as_posix()
            manifest["files"][rel] = sha256_file(file_path)

    manifest_path = dist_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=True)


def main():
    parser = argparse.ArgumentParser(description="Build FireStorm client distribution")
    parser.add_argument(
        "--dist",
        default="dist_client",
        help="Output dist directory (default: dist_client)",
    )
    parser.add_argument(
        "--version",
        default=None,
        help="Version string to embed in manifest",
    )
    args = parser.parse_args()

    root_dir = Path(__file__).resolve().parents[1]
    dist_dir = root_dir / args.dist

    version = args.version or datetime.now().strftime("%d.%m.%Y")

    build_extensions(root_dir)
    build_dist(root_dir, dist_dir)
    write_manifest(dist_dir, version)

    print(f"OK: dist created at {dist_dir}")


if __name__ == "__main__":
    main()
