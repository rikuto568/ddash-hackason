import argparse
import csv
import unicodedata
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
POPULATION_CSV_PATH = ROOT_DIR / "dataset" / "population.csv"
KIJUN_CSV_PATH = ROOT_DIR / "score" / "kijun.csv"


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


def get_population_number_by_ku(
    ku: str, population_csv_path: str | Path = POPULATION_CSV_PATH
) -> dict[str, object]:
    target = _normalize_text(ku)
    rows = _load_csv_rows(Path(population_csv_path), ["utf-8-sig", "utf-8", "cp932", "shift_jis"])

    for row in rows:
        if _normalize_text(row.get("ku", "")) == target:
            return {
                "id": row.get("id", ""),
                "ku": target,
                "number": _parse_int(row.get("number", 0)),
                "error": "",
            }

    return {"id": "", "ku": target, "number": "", "error": "KU_NOT_FOUND"}


def get_mini_score_from_kijun(
    number: int,
    name: str = "population",
    kijun_csv_path: str | Path = KIJUN_CSV_PATH,
) -> dict[str, object]:
    rows = _load_csv_rows(Path(kijun_csv_path), ["utf-8-sig", "utf-8", "cp932", "shift_jis"])
    target_name = _normalize_text(name)

    for row in rows:
        if _normalize_text(row.get("name", "")) != target_name:
            continue

        min_v = _parse_int(row.get("min", 0))
        max_raw = _normalize_text(row.get("max", ""))
        max_is_open = max_raw.lower() == "m"
        max_v = None if max_is_open else _parse_int(max_raw)

        if number < min_v:
            continue
        if max_v is None or number <= max_v:
            return {
                "kijun_id": row.get("id", ""),
                "name": target_name,
                "min": min_v,
                "max": "M" if max_is_open else max_v,
                "mini.score_population": _parse_int(row.get("mini.score", 0)),
                "error": "",
            }

    return {
        "kijun_id": "",
        "name": target_name,
        "min": "",
        "max": "",
        "mini.score_population": "",
        "error": "KIJUN_RANGE_NOT_FOUND",
    }


def get_population_mini_score_by_ku(ku: str) -> dict[str, object]:
    base = get_population_number_by_ku(ku)
    result = {
        "ku": base.get("ku", ""),
        "number": base.get("number", ""),
        "mini.score_population": "",
        "error": base.get("error", ""),
    }
    if result["error"]:
        return result

    score_info = get_mini_score_from_kijun(int(base["number"]), name="population")
    result["mini.score_population"] = score_info.get("mini.score_population", "")
    if score_info.get("error"):
        result["error"] = score_info["error"]
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="ku から population number と mini.score_population を返す")
    parser.add_argument("--ku", required=True)
    args = parser.parse_args()
    print(get_population_mini_score_by_ku(args.ku))


if __name__ == "__main__":
    main()
