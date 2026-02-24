# ddash-hackason

## 他PCで使うとき（最低限）

1. Python を入れる（推奨 `3.11`）
2. このフォルダを開く
3. 仮想環境を作る

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

4. ライブラリを入れる

```powershell
pip install -r requirements.txt
```

## 起動（必要なもの）

### 1. 住所解析サーバー

```powershell
python address_submit_server.py
```

### 2. kajuave サーバー（加重平均 API）

```powershell
uvicorn kajuave:app --host 127.0.0.1 --port 5000
```

### 3. フロント

- `app.html` を Live Server で開く（または普通に開く）

## 補足

- Google Maps Geocoding API を使う場合は `.env` に API キー設定が必要です（`.env.example` 参照）。
- このPCでは `Python 3.13.3` で `.venv` 作成と `pip install -r requirements.txt` の完了を確認済みです。
