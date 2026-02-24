import argparse
import csv
import os
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv()

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")


def geocode_address(address: str, region: str = "jp", language: str = "ja") -> dict[str, object]:
    if not API_KEY:
        raise RuntimeError("GOOGLE_MAPS_API_KEY is not set in .env")

    params = {
        "address": address,
        "key": API_KEY,
        "region": region,
        "language": language,
    }
    resp = requests.get(GEOCODE_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    status = data.get("status")
    if status != "OK":
        return {
            "address1": address,
            "lat1": "",
            "lon1": "",
            "error": status or "UNKNOWN_ERROR",
        }

    result = data["results"][0]
    loc = result["geometry"]["location"]
    return {
        "address1": address,
        "lat1": loc["lat"],
        "lon1": loc["lng"],
        "error": "",
    }


def convert_csv(input_csv: str, output_csv: str, address_col: str = "address") -> None:
    in_path = Path(input_csv)
    out_path = Path(output_csv)

    with in_path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        if address_col not in fieldnames:
            raise ValueError(f"column '{address_col}' not found: {fieldnames}")

        rows: list[dict[str, object]] = []
        for row_no, row in enumerate(reader, start=2):
            address = (row.get(address_col) or "").strip()
            if not address:
                rows.append({"address1": "", "lat1": "", "lon1": "", "error": f"row {row_no}: empty address"})
                continue

            geocoded = geocode_address(address)
            if geocoded.get("error"):
                geocoded["error"] = f"row {row_no}: {geocoded['error']}"
            rows.append(geocoded)

    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["address1", "lat1", "lon1", "error"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"saved: {out_path}")
    print(f"rows: {len(rows)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="address を geocode して address1, lat1, lon1 を作る"
    )
    parser.add_argument("--address", help="単一住所を変換して表示")
    parser.add_argument("--input-csv", help="address列を持つ入力CSV")
    parser.add_argument("--output-csv", default="address1_where_output.csv", help="出力CSV")
    parser.add_argument("--address-col", default="address", help="入力CSVの住所列名")
    args = parser.parse_args()

    if args.address:
        print(geocode_address(args.address))
        return

    if args.input_csv:
        convert_csv(args.input_csv, args.output_csv, args.address_col)
        return

    parser.error("--address または --input-csv のどちらかを指定してください")


if __name__ == "__main__":
    main()
