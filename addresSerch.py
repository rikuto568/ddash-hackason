import csv
import os
import sys
import time
import requests
from dotenv import load_dotenv
print("ここまで来た")
load_dotenv()

API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
if not API_KEY:
    raise RuntimeError("GOOGLE_MAPS_API_KEY が .env に設定されていません")

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


def geocode_one(address: str, region: str = "jp", session: requests.Session | None = None) -> dict:
    # 京都府を補完（精度UP）
    query = address if ("京都" in address) else (address + " 京都府")

    params = {
        "address": query,
        "key": API_KEY,
        "region": region,
        "language": "ja",
    }

    http = session or requests
    r = http.get(GEOCODE_URL, params=params, timeout=15)
    data = r.json()

    status = data.get("status")
    if status != "OK":
        return {"address": address, "query": query, "status": status, "error": data.get("error_message")}

    top = data["results"][0]
    loc = top["geometry"]["location"]

    return {
        "address": address,
        "query": query,
        "status": status,
        "formatted_address": top.get("formatted_address"),
        "lat": loc["lat"],
        "lng": loc["lng"],
        "location_type": top["geometry"].get("location_type"),
        "place_id": top.get("place_id"),
    }


def geocode_many(addresses: list[str], sleep_sec: float = 0.12) -> list[dict]:
    # 空文字除去 + 前後空白除去
    cleaned = []
    for a in addresses:
        a = a.strip()
        if a:
            cleaned.append(a)

    if not cleaned:
        return []

    # 重複を消して API 呼び出し回数を削減（順序は維持）
    unique_addresses = list(dict.fromkeys(cleaned))
    cache: dict[str, dict] = {}

    print(
        f"[geocode] total={len(cleaned)} unique={len(unique_addresses)} "
        f"saved_calls={len(cleaned) - len(unique_addresses)}",
        file=sys.stderr,
    )

    with requests.Session() as session:
        for i, a in enumerate(unique_addresses, start=1):
            cache[a] = geocode_one(a, session=session)
            if i < len(unique_addresses):
                time.sleep(sleep_sec)  # 連打しすぎ防止
            if i % 100 == 0 or i == len(unique_addresses):
                print(f"[geocode] {i}/{len(unique_addresses)}", file=sys.stderr)

    # 元の件数・順序で返す（重複はキャッシュ結果を再利用）
    results = []
    for a in cleaned:
        results.append(dict(cache[a]))
    return results


if __name__ == "__main__":
    # ここに住所リストを貼る（住所1, 住所2, 住所3 方式でOK）
    addresses = [
        "北区小山東元町35","北区紫野今宮町95","北区衣笠衣笠山町12"
    ]

    results = geocode_many(addresses)

    # ターミナルでは流れやすいので CSV に保存する
    out_path = "geocode_results.csv"
    ok_count = 0
    ng_count = 0

    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["address", "lat", "lng", "status", "error"])

        for r in results:
            if r["status"] == "OK":
                writer.writerow([r["address"], r["lat"], r["lng"], r["status"], ""])
                ok_count += 1
            else:
                writer.writerow([r["address"], "", "", r["status"], r.get("error", "")])
                ng_count += 1

    print(f"saved: {out_path} (OK={ok_count}, NG={ng_count}, total={len(results)})")