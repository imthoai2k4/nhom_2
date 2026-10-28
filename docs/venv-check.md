# Kiểm tra môi trường / dependency

## Phiên bản đã kiểm tra

| Package | Version |
|---|---|
| Python | 3.11 |
| fastapi | 0.115.0 |
| uvicorn | 0.30.6 |
| sqlalchemy | 2.0.36 |
| pydantic | 2.9.2 |
| python-dotenv | 1.0.1 |
| openai | 3.40.0 |
| pytest | 8.3.3 |

## Tạo venv sạch

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.lock
python -m pytest -q
python main.py
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock
pytest -q
```

## Kết quả

- `pytest -q`: **94 passed** trên môi trường hiện tại.
- `openai` 3.40.0 gọi được `https://discovery-api.intern-ai.org.cn/v1/chat/completions`.
- `requirements.lock` pin top-level dependencies; nếu cần lock đầy đủ transitive, chạy
  `pip freeze > requirements.lock` trên venv sạch.

## Ghi chú

- `pip check` trên máy dev có thể báo conflict của các package **không liên quan**
  (gtts, streamlit). Venv sạch chỉ cài `requirements.lock` sẽ không gặp các conflict này.
- SDK `google-generativeai` đã được bỏ; không cần cài cho bản hiện tại.
