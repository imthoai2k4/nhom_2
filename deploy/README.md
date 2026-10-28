# Triển khai UtilityAI (production)

## 1. Yêu cầu

- Python 3.11+
- Một domain + HTTPS (Let's Encrypt/Caddy/Nginx)
- SQLite cho demo nhỏ, hoặc PostgreSQL nếu nhiều người dùng đồng thời
- API key Qwen/Intern-AI

## 2. Cài đặt trên Linux

```bash
sudo useradd -r -m -d /opt/utilityai utilityai
sudo -u utilityai git clone <repo> /opt/utilityai
cd /opt/utilityai
sudo -u utilityai python3 -m venv .venv
sudo -u utilityai .venv/bin/pip install -r requirements.txt
sudo -u utilityai cp .env.production.example .env
sudo -u utilityai nano .env          # điền AI_API_KEY, ADMIN_PASSWORD, CORS_ORIGINS
```

Chạy thử:

```bash
cd /opt/utilityai
.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1
curl http://127.0.0.1:8000/api/health
```

## 3. systemd

```bash
sudo cp deploy/utilityai.service /etc/systemd/system/utilityai.service
sudo systemctl daemon-reload
sudo systemctl enable --now utilityai
sudo systemctl status utilityai
```

> Với SQLite, dùng **1 worker** để tránh khóa ghi. Nếu cần nhiều worker, chuyển PostgreSQL
> (`DATABASE_URL=postgresql+psycopg://...`) và cài driver tương ứng.

## 4. Nginx + HTTPS

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/utilityai
sudo ln -s /etc/nginx/sites-available/utilityai /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d your-domain.com
```

- Đổi `your-domain.com` trong `deploy/nginx.conf`.
- Bật `ENABLE_HSTS=1` trong `.env` sau khi HTTPS đã chạy ổn.
- `proxy_read_timeout 120s` để đủ cho AI (timeout 30s + retry).

## 5. Windows (NSSM)

```powershell
nssm install UtilityAI "C:\path\to\.venv\Scripts\python.exe" "-m uvicorn main:app --host 127.0.0.1 --port 8000"
nssm set UtilityAI AppDirectory "C:\path\to\project"
nssm start UtilityAI
```

Hoặc dùng `start.bat` cho môi trường dev/demo.

## 6. Healthcheck & monitor

```bash
curl -fsS https://your-domain.com/api/health
```

- Process manager: systemd/NSSM tự restart.
- Log: `journalctl -u utilityai -f` hoặc cấu hình `deploy/logrotate.conf`.
- Log AI: tìm dòng `app.services.ai_service | ai_analysis` để xem
  `source`, `finish`, `elapsed_ms`, `total_tokens`, `fallback`.

## 7. Backup / restore

```bash
# Backup (WAL-safe)
python tools/backup_db.py backup

# Restore (dừng app trước)
sudo systemctl stop utilityai
python tools/backup_db.py restore backups/utility_mgmt_YYYYmmdd_HHMMSS.db --yes
sudo systemctl start utilityai
```

## 8. Checklist trước Go-live

- [ ] `AI_API_KEY` đã điền, không nằm trong git
- [ ] `ADMIN_PASSWORD` mạnh, không dùng `admin123`
- [ ] `CORS_ORIGINS` chỉ domain thật
- [ ] HTTPS + HSTS bật
- [ ] `SEED_DEMO_DATA=0`
- [ ] Backup định kỳ (cron/Task Scheduler)
- [ ] `curl /api/health` xanh
- [ ] Chạy `pytest` trên server/CI
- [ ] Kiểm tra rate limit AI/chat
- [ ] Có kịch bản rollback (giữ DB + code bản trước)
