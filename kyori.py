import argparse
import csv
import math
from pathlib import Path


REQUIRED_COLUMNS = ["address1", "lat1", "lon1", "address2", "lat2", "lon2"]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def parse_float(value: str | None) -> float:
    if value is None or str(value).strip() == "":
        raise ValueError("empty value")
    return float(str(value).strip())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CSVの address1,lat1,lon1,address2,lat2,lon2 から距離(kyori)を計算する"
    )
    parser.add_argument("input_csv", help="入力CSVファイル")
    parser.add_argument("output_csv", nargs="?", default="kyori_output.csv", help="出力CSVファイル")
    parser.add_argument(
        "--unit",
        choices=["km", "m"],
        default="km",
        help="kyori列の単位 (default: km)",
    )
    parser.add_argument(
        "--digits",
        type=int,
        default=3,
        help="小数点以下桁数 (default: 3)",
    )
    args = parser.parse_args()

    in_path = Path(args.input_csv)
    out_path = Path(args.output_csv)

    with in_path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []

        missing = [c for c in REQUIRED_COLUMNS if c not in fieldnames]
        if missing:
            raise ValueError(f"必須列が不足しています: {missing} / columns={fieldnames}")

        out_rows = []
        error_count = 0

        for row_no, row in enumerate(reader, start=2):
            out_row = {k: row.get(k, "") for k in REQUIRED_COLUMNS}
            try:
                lat1 = parse_float(row.get("lat1"))
                lon1 = parse_float(row.get("lon1"))
                lat2 = parse_float(row.get("lat2"))
                lon2 = parse_float(row.get("lon2"))
                dist_km = haversine_km(lat1, lon1, lat2, lon2)
                kyori = dist_km if args.unit == "km" else dist_km * 1000.0
                out_row["kyori"] = round(kyori, args.digits)
            except Exception as e:
                out_row["kyori"] = ""
                out_row["error"] = f"row {row_no}: {e}"
                error_count += 1
            else:
                out_row["error"] = ""

            out_rows.append(out_row)

    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=REQUIRED_COLUMNS + ["kyori", "error"])
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"saved: {out_path}")
    print(f"rows: {len(out_rows)}")
    print(f"errors: {error_count}")
    print(f"unit: {args.unit}")


if __name__ == "__main__":
    main()
