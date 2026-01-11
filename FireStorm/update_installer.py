"""
Standalone updater used by the client when a new update.zip is downloaded.
Keep this file dependency-free (no "modules" imports) so it can run with the
system Python.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile


def load_config(base_dir):
    config_path = os.path.join(base_dir, "settings", "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def verify_signature(archive_path, signature_path, public_key_path):
    gpg = shutil.which("gpg")
    if not gpg:
        return False
    if not (os.path.exists(signature_path) and os.path.exists(public_key_path)):
        return False
    with tempfile.TemporaryDirectory() as gnupg_home:
        env = os.environ.copy()
        env["GNUPGHOME"] = gnupg_home
        import_result = subprocess.run(
            [gpg, "--import", public_key_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        if import_result.returncode != 0:
            return False
        verify_result = subprocess.run(
            [gpg, "--verify", signature_path, archive_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        return verify_result.returncode == 0


def safe_extract(zip_ref, member, target_dir):
    target_dir = os.path.abspath(target_dir)
    dest_path = os.path.abspath(os.path.join(target_dir, member))
    if not dest_path.startswith(target_dir + os.sep) and dest_path != target_dir:
        raise ValueError(f"Unsafe path in archive: {member}")
    zip_ref.extract(member, target_dir)
    return dest_path


def get_app_target(app_dir):
    if not app_dir:
        return None
    app_dir = os.path.abspath(app_dir)
    if sys.platform == "darwin" and app_dir.endswith(os.path.join("Contents", "MacOS")):
        return os.path.abspath(os.path.join(app_dir, "..", ".."))
    return app_dir


def allowed_app_item(name):
    allowed = {
        "FireStorm",
        "FireStorm.exe",
        "FireStormUploader",
        "FireStormUploader.exe",
        "_internal",
        "FireStorm.app",
        "FireStormUploader.app",
    }
    return name in allowed


def main():
    base_dir = os.getenv("FIRESTORM_BASE", os.getcwd())
    app_dir = os.getenv("FIRESTORM_APP_DIR")
    if not app_dir:
        app_hint = os.path.join(base_dir, "app_dir.txt")
        if os.path.isfile(app_hint):
            try:
                with open(app_hint, "r", encoding="utf-8") as file:
                    app_dir = file.read().strip() or None
            except Exception:
                app_dir = None

    config = load_config(base_dir)
    require_signature = bool(config.get("require_signature", False))
    public_key_path = config.get("public_key_path", os.path.join(base_dir, "settings", "public.key"))
    allow_app_update = bool(config.get("allow_app_update", False))

    update_zip = os.path.join(base_dir, "update.zip")
    if os.path.exists(update_zip):
        if require_signature:
            sig_path = update_zip + ".asc"
            if not os.path.exists(sig_path):
                print("Подпись обновления не найдена. Установка остановлена.")
                raise SystemExit(1)
            if not verify_signature(update_zip, sig_path, public_key_path):
                print("Подпись обновления невалидна. Установка остановлена.")
                raise SystemExit(1)

        app_target = get_app_target(app_dir) if allow_app_update else None
        with zipfile.ZipFile(update_zip, "r") as zip_ref:
            app_items = []
            for file in zip_ref.namelist():
                if file.startswith("app/"):
                    app_items.append(file)
                    continue
                try:
                    safe_extract(zip_ref, file, base_dir)
                except Exception:
                    print(f"Ошибка при извлечении файла: {file}. Пропускаем его.")

            if allow_app_update and app_target and app_items:
                with tempfile.TemporaryDirectory() as tmp_dir:
                    for file in app_items:
                        try:
                            safe_extract(zip_ref, file, tmp_dir)
                        except Exception:
                            print(f"Ошибка при извлечении app-файла: {file}. Пропускаем его.")
                    app_root = os.path.join(tmp_dir, "app")
                    if os.path.isdir(app_root):
                        for name in os.listdir(app_root):
                            if not allowed_app_item(name):
                                continue
                            src_path = os.path.join(app_root, name)
                            dst_path = os.path.join(app_target, name)
                            if os.path.isdir(dst_path):
                                shutil.rmtree(dst_path)
                            if os.path.isdir(src_path):
                                shutil.copytree(src_path, dst_path)
                            else:
                                shutil.copy2(src_path, dst_path)
                            if not sys.platform.startswith("win") and name in ("FireStorm", "FireStormUploader"):
                                try:
                                    os.chmod(dst_path, 0o755)
                                except Exception:
                                    pass

            comment = zip_ref.comment.decode("utf-8")

        ver_path = os.path.join(base_dir, "ver")
        if os.path.isdir(ver_path):
            ver_path = os.path.join(ver_path, "ver")
        with open(ver_path, "w", encoding="utf-8") as ver_file:
            ver_file.write(comment)

        try:
            os.remove(update_zip)
        except Exception:
            pass
        if os.path.exists(update_zip + ".asc"):
            try:
                os.remove(update_zip + ".asc")
            except Exception:
                pass

    exe_name = "FireStorm.exe" if sys.platform.startswith("win") else "FireStorm"
    if app_dir and os.path.exists(os.path.join(app_dir, exe_name)):
        subprocess.Popen([os.path.join(app_dir, exe_name)], shell=False)
    else:
        script_path = os.path.join(base_dir, "FireStorm.py")
        python_path = sys.executable
        subprocess.Popen([python_path, script_path], shell=False)


if __name__ == "__main__":
    main()
