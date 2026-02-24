import argparse
import csv
import os
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv()

API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
REVERSE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

KYOTO_WARDS = [
    "北区",
    "上京区",
    "左京区",
    "中京区",
    "東山区",
    "下京区",
    "南区",
    "右京区",
    "西京区",
    "伏見区",
    "山科区",
]


def _extract_ward_from_text(text: str) -> str | None:
    if not text:
        return None
    for ward in KYOTO_WARDS:
        if ward in text:
            return ward
    return None


def detect_kyoto_ku(lat1: float, lon1: float, language: str = "ja") -> dict[str, object]:
    if not API_KEY:
        raise RuntimeError("GOOGLE_MAPS_API_KEY is not set in .env")

    params = {
        "latlng": f"{lat1},{lon1}",
        "key": API_KEY,
        "language": language,
        "region": "jp",
    }

    resp = requests.get(REVERSE_GEOCODE_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    status = data.get("status")
    if status != "OK":
        return {
            "lat1": lat1,
            "lon1": lon1,
            "ku": "",
            "error": status or "UNKNOWN_ERROR",
        }

    for result in data.get("results", []):
        # Prefer explicit address components first.
        for comp in result.get("address_components", []):
            ward = _extract_ward_from_text(comp.get("long_name", ""))
            if ward:
                return {"lat1": lat1, "lon1": lon1, "ku": ward, "error": ""}

        # Fallback to formatted address text.
        ward = _extract_ward_from_text(result.get("formatted_address", ""))
        if ward:
            return {"lat1": lat1, "lon1": lon1, "ku": ward, "error": ""}

    return {
        "lat1": lat1,
        "lon1": lon1,
        "ku": "",
        "error": "KYOTO_WARD_NOT_FOUND",
    }


def detect_kyoto_ku_from_values(lat1: object, lon1: object) -> dict[str, object]:
    return detect_kyoto_ku(float(lat1), float(lon1))


def convert_csv(input_csv: str, output_csv: str, lat_col: str = "lat1", lon_col: str = "lon1") -> None:
    in_path = Path(input_csv)
    out_path = Path(output_csv)

    with in_path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        if lat_col not in fieldnames or lon_col not in fieldnames:
            raise ValueError(f"required columns not found: {lat_col}, {lon_col} / {fieldnames}")

        out_rows: list[dict[str, object]] = []
        for row_no, row in enumerate(reader, start=2):
            out_row = dict(row)
            try:
                lat1 = float(str(row.get(lat_col, "")).strip())
                lon1 = float(str(row.get(lon_col, "")).strip())
                result = detect_kyoto_ku(lat1, lon1)
                out_row["ku"] = result.get("ku", "")
                out_row["error"] = result.get("error", "")
            except Exception as e:
                out_row["ku"] = ""
                out_row["error"] = f"row {row_no}: {e}"
            out_rows.append(out_row)

    out_fields = list(fieldnames)
    if "ku" not in out_fields:
        out_fields.append("ku")
    if "error" not in out_fields:
        out_fields.append("error")

    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"saved: {out_path}")
    print(f"rows: {len(out_rows)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="lat1/lon1 から京都市の区（11区のどれか）を判定する"
    )
    parser.add_argument("--lat1", type=float, help="latitude")
    parser.add_argument("--lon1", type=float, help="longitude")
    parser.add_argument("--input-csv", help="lat1,lon1 を持つ入力CSV")
    parser.add_argument("--output-csv", default="zahyou_ku_output.csv", help="出力CSV")
    parser.add_argument("--lat-col", default="lat1", help="緯度列名")
    parser.add_argument("--lon-col", default="lon1", help="経度列名")
    args = parser.parse_args()

    if args.lat1 is not None and args.lon1 is not None:
        print(detect_kyoto_ku(args.lat1, args.lon1))
        return

    if args.input_csv:
        convert_csv(args.input_csv, args.output_csv, args.lat_col, args.lon_col)
        return

    parser.error("`--lat1 --lon1` または `--input-csv` を指定してください")


if __name__ == "__main__":
    main()
