import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path


def run(cmd, cwd=None):
    subprocess.check_call(cmd, cwd=cwd)


def add_dir_to_zip(zipf, directory, base_dir):
    for root, _, files in os.walk(directory):
        for name in files:
            file_path = Path(root) / name
            rel = file_path.relative_to(base_dir).as_posix()
            zipf.write(file_path, rel)


def add_dir_to_zip_with_prefix(zipf, directory, base_dir, prefix):
    for root, _, files in os.walk(directory):
        for name in files:
            file_path = Path(root) / name
            rel = file_path.relative_to(base_dir).as_posix()
            zipf.write(file_path, f"{prefix}/{rel}")


def sign_if_requested(zip_path, key_id=None):
    gpg = shutil.which("gpg")
    if not gpg:
        print("WARN: gpg not found, skipping signature")
        return None
    cmd = [gpg, "--batch", "--yes", "--detach-sign", "--armor"]
    passphrase = os.getenv("GPG_PASSPHRASE")
    if passphrase:
        cmd += ["--pinentry-mode", "loopback", "--passphrase", passphrase]
    if key_id:
        cmd += ["--local-user", key_id]
    cmd.append(str(zip_path))
    run(cmd)
    return str(zip_path) + ".asc"


def main():
    parser = argparse.ArgumentParser(description="Build update_v2.zip from FireStorm dist")
    parser.add_argument("--version", default=None, help="Version string")
    parser.add_argument("--news", default=None, help="Path to news.txt")
    parser.add_argument("--dist", default="dist_client", help="Dist directory")
    parser.add_argument("--app-dir", default=None, help="App directory to include under app/")
    parser.add_argument("--out", default=None, help="Output zip")
    parser.add_argument("--sign", action="store_true", help="Create GPG signature")
    parser.add_argument("--gpg-key", default=None, help="GPG key id/email")
    args = parser.parse_args()

    root_dir = Path(__file__).resolve().parents[1]
    dist_dir = root_dir / args.dist
    if not dist_dir.exists():
        run([sys.executable, "tools/build_client.py", "--dist", args.dist], cwd=root_dir)

    version = args.version or datetime.now().strftime("%d.%m.%Y")
    if args.out:
        out_name = args.out
    else:
        out_name = f"update_{version}.zip"
    out_zip = root_dir / out_name

    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
        add_dir_to_zip(zipf, dist_dir, dist_dir)
        if args.app_dir:
            app_dir = Path(args.app_dir)
            if app_dir.exists():
                add_dir_to_zip_with_prefix(zipf, app_dir, app_dir, "app")
        if args.news:
            zipf.write(args.news, "news.txt")
        zipf.comment = version.encode("utf-8")

    sig_path = None
    if args.sign:
        sig_path = sign_if_requested(out_zip, args.gpg_key)

    print(f"OK: update created at {out_zip}")
    if sig_path:
        print(f"OK: signature created at {sig_path}")


if __name__ == "__main__":
    main()
