import argparse
import subprocess
import sys
from datetime import datetime


def run(cmd):
    subprocess.check_call(cmd)


def main():
    parser = argparse.ArgumentParser(description="Auto-build FireStorm client + update archive")
    parser.add_argument("--version", default=None, help="Version string")
    parser.add_argument("--news", default=None, help="Path to news.txt")
    parser.add_argument("--dist", default="dist_client", help="Dist directory")
    parser.add_argument("--out", default=None, help="Output zip")
    parser.add_argument("--sign", action="store_true", help="Create GPG signature")
    parser.add_argument("--gpg-key", default=None, help="GPG key id/email")
    args = parser.parse_args()

    version = args.version or datetime.now().strftime("%d.%m.%Y")

    run([sys.executable, "tools/build_client.py", "--dist", args.dist, "--version", version])

    cmd = [
        sys.executable,
        "tools/build_update.py",
        "--dist",
        args.dist,
        "--version",
        version,
    ]
    if args.out:
        cmd += ["--out", args.out]
    if args.news:
        cmd += ["--news", args.news]
    if args.sign:
        cmd.append("--sign")
        if args.gpg_key:
            cmd += ["--gpg-key", args.gpg_key]

    run(cmd)

    print("OK: autobuild finished")


if __name__ == "__main__":
    main()
