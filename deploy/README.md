# Deployment Notes (Linux)

## 1) Env
- Copy `.env.example` to `.env` and fill values.
- Ensure `FILES_DIR` and `QUARANTINE_DIR` exist and are writable by the service user.

## 2) Systemd
- Copy `deploy/fstracker.service` to `/etc/systemd/system/fstracker.service`.
- Adjust `WorkingDirectory`, `EnvironmentFile`, `ExecStart`, `User`, `Group` as needed.
- Enable and start:
  - `systemctl daemon-reload`
  - `systemctl enable fstracker`
  - `systemctl start fstracker`

## 3) Nginx
- Use `deploy/nginx_fstracker.conf` as a starting point.
- Adjust `server_name` and SSL as needed.
- Ensure `client_max_body_size` matches `MAX_UPLOAD_SIZE_MB`.

## 4) ClamAV (optional)
- Install:
  - Debian/Ubuntu: `apt install clamav clamav-daemon`
- Update signatures:
  - `freshclam`
- Enable scanning:
  - Set `CLAMAV_ENABLED=1` in `.env`
  - Optionally set `CLAMAV_CMD=clamdscan` or `clamscan`
  - Choose policy with `QUARANTINE_ACTION=quarantine|delete|ignore`

## 5) Redis worker (optional)
- Enable Redis:
  - Set `REDIS_ENABLED=1` and `REDIS_URL` in `.env`
- Run worker:
  - `python3 server_app/workers/scan_worker.py`
  - `python3 server_app/workers/av_worker.py`
