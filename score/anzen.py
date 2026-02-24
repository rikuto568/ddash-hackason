import argparse
import importlib.util
from pathlib import Path


SCORE_DIR = Path(__file__).resolve().parent
MINI_SCORE_DIR = SCORE_DIR / "mini.score"
HANZAI_PATH = MINI_SCORE_DIR / "hanzai.py"
JIKO_PATH = MINI_SCORE_DIR / "jiko.py"


def add_two_numbers(a: float, b: float) -> float:
    return float(a) + float(b)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def add_mini_scores(mini_score_hanzai: int | float, mini_score_jiko: int | float) -> float:
    return add_two_numbers(mini_score_hanzai, mini_score_jiko)


def add_mini_scores_from_results(hanzai_result: dict, jiko_result: dict) -> dict[str, object]:
    """
    hanzai.py / jiko.py の返り値 dict を受け取り、mini score を足して返す
    """
    result = {
        "mini.number": 2,
        "mini.score_hanzai": hanzai_result.get("mini.score_hanzai", ""),
        "mini.score_jiko": jiko_result.get("mini.score_jiko", ""),
        "mini.score": "",
        "anzen_score_sum": "",
        "error": "",
    }

    if hanzai_result.get("error"):
        result["error"] = f"hanzai: {hanzai_result['error']}"
        return result
    if jiko_result.get("error"):
        result["error"] = f"jiko: {jiko_result['error']}"
        return result

    try:
        total = add_mini_scores(
            float(hanzai_result["mini.score_hanzai"]),
            float(jiko_result["mini.score_jiko"]),
        )
        result["anzen_score_sum"] = total
        # 別ファイルへ渡す用の共通キー
        result["mini.score"] = total
    except Exception as e:
        result["error"] = str(e)

    return result


def get_anzen_score_by_ku(ku: str) -> dict[str, object]:
    """
    ku を受け取り、mini.score/hanzai.py と mini.score/jiko.py を呼んで合計点を返す
    """
    hanzai_mod = _load_module("mini_score_hanzai", HANZAI_PATH)
    jiko_mod = _load_module("mini_score_jiko", JIKO_PATH)

    hanzai_result = hanzai_mod.get_hanzai_mini_score_by_ku(ku)
    jiko_result = jiko_mod.get_jiko_mini_score_by_ku(ku)
    sum_result = add_mini_scores_from_results(hanzai_result, jiko_result)

    return {
        "ku": ku,
        "mini.number": sum_result.get("mini.number", 2),
        "hanzai_number": hanzai_result.get("number", ""),
        "mini.score_hanzai": hanzai_result.get("mini.score_hanzai", ""),
        "jiko_number": jiko_result.get("number", ""),
        "mini.score_jiko": jiko_result.get("mini.score_jiko", ""),
        "mini.score": sum_result.get("mini.score", ""),
        "anzen_score_sum": sum_result.get("anzen_score_sum", ""),
        "error": sum_result.get("error", ""),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="hanzai/jiko の mini.score を足して anzen score を作る"
    )
    parser.add_argument("--ku", help="区名を指定して hanzai+jiko の mini score 合計を計算")
    parser.add_argument("a", nargs="?", type=float, help="直接足す1つ目の数値")
    parser.add_argument("b", nargs="?", type=float, help="直接足す2つ目の数値")
    args = parser.parse_args()

    if args.ku:
        print(get_anzen_score_by_ku(args.ku))
        return

    if args.a is not None and args.b is not None:
        print(add_two_numbers(args.a, args.b))
        return

    parser.error("--ku または a b を指定してください")


if __name__ == "__main__":
    main()
