# ddash-hackason (portable setup)

## What this project needs on another PC
- Python 3.11+ (3.10+ should also work)
- Google Maps API key (`Geocoding API` enabled)

## Setup
```powershell
cd C:\path\to\ddash-hackason
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env` に `GOOGLE_MAPS_API_KEY` を設定してください。

## Run (backend for address parsing / scores)
```powershell
python address_submit_server.py
```

Default: `http://127.0.0.1:8000`

環境変数で変更可能:
```powershell
$env:ADDRESS_SERVER_HOST="0.0.0.0"
$env:ADDRESS_SERVER_PORT="8000"
python address_submit_server.py
```

## Run (kajuave API, optional but recommended)
`/weighted` を使うだけなら `calculateseg.py` がなくても起動可能です。

```powershell
uvicorn kajuave:app --host 127.0.0.1 --port 5000
```

## Frontend (`app.html`)
- Live Server でも動作します
- デフォルト接続先は現在のPCのホスト名ベースで推定:
  - address API: `http://<current-host>:8000`
  - kajuave API: `http://<current-host>:5000`

必要ならブラウザコンソールで上書き:
```js
localStorage.setItem("ADDRESS_API_BASE", "http://127.0.0.1:8000");
localStorage.setItem("KAJUAVE_API_BASE", "http://127.0.0.1:5000");
```

## Git push / shared use notes
- `.env` は `.gitignore` 済みなので push しない
- `dataset/*.csv`, `score/kijun.csv` は repo に含める
- 他PCでは `.env` だけ作れば同じ構成で動かせます
