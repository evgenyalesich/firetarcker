# Client Build Automation

## Why
- Cython compile of modules to reduce source visibility.
- Deterministic dist folder with compiled extensions only.
- Manifest for integrity checks.
- Optional GPG signature for update archive.

## Build dist
```
python3 tools/build_client.py --version 10.01.2026
```
Creates `dist_client/` with:
- root layout like the installed app:
  - `FireStorm.py`, `uploader.py`, `update_installer.py`
  - `settings/`, `layouts/`, `img/`
  - `modules/*.so` (compiled)
- `manifest.json` (SHA256 checksums)

## Build update archive
```
python3 tools/build_update.py --version 10.01.2026 --news news.txt
```
Output: `update_10.01.2026.zip`
Creates an update archive with a version comment and `news.txt`.

## Optional signature
```
python3 tools/build_update.py --version 10.01.2026 --sign --gpg-key you@example.com
```

## Autobuild (all-in-one)
```
python3 tools/autobuild.py --version 10.01.2026 --news news.txt --sign --gpg-key you@example.com
```

## CI signing (GitHub Actions)
Secrets required:
- `GPG_PRIVATE_KEY` (ASCII-armored private key)
- `GPG_PASSPHRASE` (if your key is encrypted)
- `GPG_KEY_ID` (optional, email or key id)
Produces `update_<version>.zip.asc` if `gpg` is available.

## Notes
- Full protection on client is impossible; security comes from server-side logic.
- Keep sensitive logic and data on the server.
