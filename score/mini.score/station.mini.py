import argparse
import csv
import sys
import unicodedata
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from kyori import distance_between_points  # noqa: E402


STATION_CSV_PATH = ROOT_DIR / "dataset" / "station.csv"
KIJUN_CSV_PATH = ROOT_DIR / "score" / "kijun.csv"


def _parse_float(value: object) -> float:
    return float(str(value).strip().replace(",", ""))


def _parse_int(value: object) -> int:
    return int(str(value).strip().replace(",", ""))


def _normalize_text(value: object) -> str:
    return unicodedata.normalize("NFKC", str(value)).strip()


def _load_csv_rows(path: Path, encodings: list[str]) -> list[dict[str, str]]:
    last_error = None
    for enc in encodings:
        try:
            with path.open("r", newline="", encoding=enc) as f:
                return list(csv.DictReader(f))
        except Exception as e:
            last_error = e
    raise RuntimeError(f"failed to read csv: {path}") from last_error


def find_nearest_station(lat1: float, lon1: float, station_csv_path: str | Path = STATION_CSV_PATH) -> dict[str, object]:
    """
    lat1/lon1 を受け取り、dataset/station.csv の最短駅を返す
    """
    path = Path(station_csv_path)
    rows = _load_csv_rows(path, ["utf-8-sig", "utf-8", "cp932", "shift_jis"])

    nearest: dict[str, object] | None = None
    min_distance_m: float | None = None

    for row in rows:
        try:
            lat2 = _parse_float(row.get("lat", ""))
            lon2 = _parse_float(row.get("lng", ""))
        except Exception:
            continue

        dist_m = distance_between_points(lat1, lon1, lat2, lon2, unit="m", digits=1)
        if min_distance_m is None or float(dist_m) < min_distance_m:
            min_distance_m = float(dist_m)
            nearest = {
                "station_id": row.get("id", ""),
                "station_name": row.get("name", ""),
                "station_address": row.get("address", ""),
                "lat2": lat2,
                "lon2": lon2,
                "station_distance_m": dist_m,
                "error": "",
            }

    if nearest is None:
        return {
            "station_id": "",
            "station_name": "",
            "station_address": "",
            "lat2": "",
            "lon2": "",
            "station_distance_m": "",
            "error": "STATION_NOT_FOUND",
        }
    return nearest


def get_mini_score_station_from_kijun(
    distance_m: float | int,
    kijun_csv_path: str | Path = KIJUN_CSV_PATH,
) -> dict[str, object]:
    """
    score/kijun.csv の name=eki を使い、距離(m)から mini.score_station を返す
    """
    path = Path(kijun_csv_path)
    rows = _load_csv_rows(path, ["utf-8-sig", "utf-8", "cp932", "shift_jis"])
    distance_int = int(float(distance_m))

    for row in rows:
        if _normalize_text(row.get("name", "")) != "eki":
            continue

        min_v = _parse_int(row.get("min", 0))
        max_raw = _normalize_text(row.get("max", ""))
        max_is_open = max_raw.lower() == "m"
        max_v = None if max_is_open else _parse_int(max_raw)

        if distance_int < min_v:
            continue
        if max_v is None or distance_int <= max_v:
            return {
                "kijun_id": row.get("id", ""),
                "mini.score_station": _parse_int(row.get("mini.score", 0)),
                "error": "",
            }

    return {"kijun_id": "", "mini.score_station": "", "error": "KIJUN_RANGE_NOT_FOUND"}


def get_station_mini_score_by_latlon(lat1: float, lon1: float) -> dict[str, object]:
    """
    address1_where.py の結果から受け取る lat1/lon1 を入口に、
    最短駅・距離(m)・mini.score_station を返す
    """
    result = {
        "lat1": float(lat1),
        "lon1": float(lon1),
        "lat2": "",
        "lon2": "",
        "station_name": "",
        "station_address": "",
        "station_distance_m": "",
        "mini.score_station": "",
        "error": "",
    }

    nearest = find_nearest_station(float(lat1), float(lon1))
    if nearest.get("error"):
        result["error"] = nearest["error"]
        return result

    result["lat2"] = nearest.get("lat2", "")
    result["lon2"] = nearest.get("lon2", "")
    result["station_name"] = nearest.get("station_name", "")
    result["station_address"] = nearest.get("station_address", "")
    result["station_distance_m"] = nearest.get("station_distance_m", "")

    score_info = get_mini_score_station_from_kijun(float(result["station_distance_m"]))
    result["mini.score_station"] = score_info.get("mini.score_station", "")
    if score_info.get("error"):
        result["error"] = score_info["error"]

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="lat1/lon1 から最短駅と距離(m)、mini.score_station を取得する"
    )
    parser.add_argument("--lat1", type=float, required=True, help="入力緯度")
    parser.add_argument("--lon1", type=float, required=True, help="入力経度")
    args = parser.parse_args()
    print(get_station_mini_score_by_latlon(args.lat1, args.lon1))


if __name__ == "__main__":
    main()
