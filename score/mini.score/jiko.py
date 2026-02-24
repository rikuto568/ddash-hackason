import argparse
import csv
import unicodedata
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
JIKO_CSV_PATH = ROOT_DIR / "dataset" / "jiko.csv"
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


def get_jiko_number_by_ku(ku: str, jiko_csv_path: str | Path = JIKO_CSV_PATH) -> dict[str, object]:
    """
    ku を受け取り dataset/jiko.csv の number を返す
    """
    target = _normalize_text(ku)
    path = Path(jiko_csv_path)
    rows = _load_csv_rows(path, ["utf-8-sig", "utf-8", "cp932", "shift_jis"])

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
    name: str = "jiko",
    kijun_csv_path: str | Path = KIJUN_CSV_PATH,
) -> dict[str, object]:
    """
    score/kijun.csv の name=jiko 行から number の範囲に対応する mini.score を返す
    """
    path = Path(kijun_csv_path)
    rows = _load_csv_rows(path, ["utf-8-sig", "utf-8", "cp932", "shift_jis"])

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
        if (max_v is None) or (number <= max_v):
            return {
                "kijun_id": row.get("id", ""),
                "name": target_name,
                "min": min_v,
                "max": "M" if max_is_open else max_v,
                "mini.score_jiko": _parse_int(row.get("mini.score", 0)),
                "error": "",
            }

    return {
        "kijun_id": "",
        "name": target_name,
        "min": "",
        "max": "",
        "mini.score_jiko": "",
        "error": "KIJUN_RANGE_NOT_FOUND",
    }


def get_jiko_mini_score_by_ku(ku: str) -> dict[str, object]:
    """
    ku -> number -> mini.score_jiko
    別ファイルへ渡しやすい形式で返す
    """
    base = get_jiko_number_by_ku(ku)
    result = {
        "ku": base.get("ku", ""),
        "number": base.get("number", ""),
        "mini.score_jiko": "",
        "error": base.get("error", ""),
    }
    if result["error"]:
        return result

    score_info = get_mini_score_from_kijun(int(base["number"]), name="jiko")
    result["mini.score_jiko"] = score_info.get("mini.score_jiko", "")
    if score_info.get("error"):
        result["error"] = score_info["error"]
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ku から jiko number と mini.score_jiko を取得する"
    )
    parser.add_argument("--ku", required=True, help="区名（例: 北区）")
    args = parser.parse_args()
    print(get_jiko_mini_score_by_ku(args.ku))


if __name__ == "__main__":
    main()
