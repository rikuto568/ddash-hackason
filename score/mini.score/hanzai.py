import argparse
import csv
import unicodedata
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
HANZAI_CSV_PATH = ROOT_DIR / "dataset" / "hanzai.csv"
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


def get_hanzai_number_by_ku(ku: str, hanzai_csv_path: str | Path = HANZAI_CSV_PATH) -> dict[str, object]:
    """
    ku を受け取り dataset/hanzai.csv の number を返す
    """
    target = _normalize_text(ku)
    path = Path(hanzai_csv_path)
    # UTF-8 を先に試す。cp932 を先にすると文字化けでも例外にならず誤読しやすい。
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
    name: str = "hanzai",
    kijun_csv_path: str | Path = KIJUN_CSV_PATH,
) -> dict[str, object]:
    """
    score/kijun.csv の name 行から number が入る範囲を探し mini.score を返す
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
                "mini.score_hanzai": _parse_int(row.get("mini.score", 0)),
                "error": "",
            }

    return {
        "kijun_id": "",
        "name": target_name,
        "min": "",
        "max": "",
        "mini.score_hanzai": "",
        "error": "KIJUN_RANGE_NOT_FOUND",
    }


def get_hanzai_mini_score_by_ku(ku: str) -> dict[str, object]:
    """
    ku -> number -> mini.score_hanzai
    別ファイルへ渡しやすい形式で返す
    """
    base = get_hanzai_number_by_ku(ku)
    result = {
        "ku": base.get("ku", ""),
        "number": base.get("number", ""),
        "mini.score_hanzai": "",
        "error": base.get("error", ""),
    }
    if result["error"]:
        return result

    score_info = get_mini_score_from_kijun(int(base["number"]), name="hanzai")
    result["mini.score_hanzai"] = score_info.get("mini.score_hanzai", "")
    if score_info.get("error"):
        result["error"] = score_info["error"]
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ku から hanzai number と mini.score_hanzai を取得する"
    )
    parser.add_argument("--ku", required=True, help="区名（例: 北区）")
    args = parser.parse_args()
    print(get_hanzai_mini_score_by_ku(args.ku))


if __name__ == "__main__":
    main()
