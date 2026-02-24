import argparse
import csv
import math
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
KOKYOU_CSV = BASE_DIR / "dataset" / "kokyou.csv"


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _parse_float(v: object) -> float:
    return float(str(v).strip())


def find_nearest_kokyou(lat1: float, lon1: float, csv_path: str | Path = KOKYOU_CSV) -> dict[str, object]:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"kokyou csv not found: {path}")

    nearest: dict[str, object] | None = None
    min_km: float | None = None

    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        if "lat" not in fieldnames or "lng" not in fieldnames:
            raise ValueError(f"lat/lng columns not found: {fieldnames}")

        for row_no, row in enumerate(reader, start=2):
            try:
                lat2 = _parse_float(row.get("lat", ""))
                lon2 = _parse_float(row.get("lng", ""))
            except Exception:
                continue

            km = haversine_km(lat1, lon1, lat2, lon2)
            if min_km is None or km < min_km:
                min_km = km
                nearest = {
                    "lat1": lat1,
                    "lon1": lon1,
                    "lat2": lat2,
                    "lon2": lon2,
                    "kyori_km": round(km, 3),
                    "id": row.get("id", ""),
                    "name1": row.get("name1", ""),
                    "name2": row.get("name2", ""),
                    "address": row.get("address", ""),
                    "source_row": row_no,
                }

    if nearest is None:
        raise RuntimeError("no valid lat/lng rows found in kokyou.csv")
    return nearest


def assign_lat2_lon2_from_address1_result(result_from_address1_where: dict[str, object]) -> dict[str, object]:
    """
    address1_where.py の結果（address1, lat1, lon1 を含むdict）を受け取り、
    最短の公共施設を探して lat2/lon2 を追加して返す。
    """
    lat1 = _parse_float(result_from_address1_where.get("lat1", ""))
    lon1 = _parse_float(result_from_address1_where.get("lon1", ""))

    nearest = find_nearest_kokyou(lat1, lon1)
    merged = dict(result_from_address1_where)
    merged["lat2"] = nearest["lat2"]
    merged["lon2"] = nearest["lon2"]
    merged["kokyou_name"] = nearest.get("name1") or nearest.get("name2", "")
    merged["kokyou_address"] = nearest.get("address", "")
    merged["kokyou_kyori_km"] = nearest["kyori_km"]
    return merged


def main() -> None:
    parser = argparse.ArgumentParser(
        description="lat1/lon1 から dataset/kokyou.csv の最短公共施設を探して lat2/lon2 を返す"
    )
    parser.add_argument("--lat1", type=float, required=True, help="input latitude")
    parser.add_argument("--lon1", type=float, required=True, help="input longitude")
    parser.add_argument("--csv", default=str(KOKYOU_CSV), help="kokyou csv path")
    args = parser.parse_args()

    result = find_nearest_kokyou(args.lat1, args.lon1, args.csv)
    print(result)


if __name__ == "__main__":
    main()
