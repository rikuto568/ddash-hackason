from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from typing import Iterable

# バックエンド用の保持変数（必要なら参照可能）
RAW_VALUES: list[float] = []
AXIS_VALUES: list[int] = []
NORMALIZED_VALUES: list[float] = []
SCORE_MAP: dict[str, float] = {}

# 正規化の分母単位（axis * 10）
DENOMINATOR_UNIT: float = 10.0


def normalize_to_unit(value: float, max_value: float, min_value: float = 0.0) -> float:
    """
    値を 0〜1 に正規化する
    normalized = (value - min_value) / (max_value - min_value)
    """
    if max_value <= min_value:
        raise ValueError("max_value must be greater than min_value")
    if value < min_value or value > max_value:
        raise ValueError(f"value({value}) is out of range: {min_value} - {max_value}")
    return (value - min_value) / (max_value - min_value)


def normalize_values(values: Iterable[float], axis_values: Iterable[int]) -> list[float]:
    """
    複数の値を正規化する
    各値の分母は (対応する axis * DENOMINATOR_UNIT)
    例:
      values=[8,5,10], axis_values=[1,2,3]
      -> [8/10, 5/20, 10/30]
    """
    data = [float(v) for v in values]
    axes = [int(a) for a in axis_values]

    if not data:
        raise ValueError("values is empty")
    if len(data) != len(axes):
        raise ValueError("values and axis_values must have the same length")
    if any(a <= 0 for a in axes):
        raise ValueError("axis_values must be >= 1")

    normalized: list[float] = []
    for value, axis in zip(data, axes):
        denominator = float(axis) * DENOMINATOR_UNIT
        normalized.append(normalize_to_unit(value, denominator))

    return normalized


def build_score_map(normalized_values: Iterable[float]) -> dict[str, float]:
    """
    正規化値を SCORE_1..SCORE_n に格納する
    例: [0.8, 0.25] -> {"SCORE_1":0.8, "SCORE_2":0.25}
    """
    return {f"SCORE_{index}": float(value) for index, value in enumerate(normalized_values, start=1)}


def normalize_and_store(values: Iterable[float], axis_values: Iterable[int]) -> dict[str, float]:
    """
    複数値を正規化し、モジュール変数にも保存して返す
    """
    global RAW_VALUES, AXIS_VALUES, NORMALIZED_VALUES, SCORE_MAP

    RAW_VALUES = [float(v) for v in values]
    AXIS_VALUES = [int(a) for a in axis_values]
    NORMALIZED_VALUES = normalize_values(RAW_VALUES, AXIS_VALUES)
    SCORE_MAP = build_score_map(NORMALIZED_VALUES)
    return SCORE_MAP


def get_score_list() -> list[float]:
    return list(NORMALIZED_VALUES)


def normalize_mini_score_result(result: dict[str, object]) -> dict[str, object]:
    """
    汎用: mini.number / mini.score を持つ dict を受け取り、正規化後の score を返す。
    既存の正規化式は normalize_values() をそのまま使う。
    """
    if "mini.number" not in result or "mini.score" not in result:
        raise KeyError("result must contain 'mini.number' and 'mini.score'")

    mini_number = int(float(result["mini.number"]))
    mini_score = float(result["mini.score"])
    normalized_score = normalize_values([mini_score], [mini_number])[0]

    out = dict(result)
    out["score"] = normalized_score
    return out


def _load_module_from_path(path: Path, module_name: str = "dynamic_mod"):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalize_from_function_result(module_path: str | Path, function_name: str, *args) -> dict[str, object]:
    """
    汎用: 任意のPythonファイルの関数戻り値(dict)から mini.number / mini.score を受けて正規化する
    例: score/anzen.py の get_anzen_score_by_ku("中京区")
    """
    mod = _load_module_from_path(Path(module_path))
    fn = getattr(mod, function_name)
    result = fn(*args)
    if not isinstance(result, dict):
        raise TypeError("target function must return dict")
    return normalize_mini_score_result(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="mini.number と mini.score を受け取り、正規化後の score を返す（式は既存ロジック）"
    )
    parser.add_argument("--mini-number", type=float, help="使った mini.score の数")
    parser.add_argument("--mini-score", type=float, help="合計 mini.score")
    parser.add_argument("--anzen-ku", help="score/anzen.py の結果を読み込んで正規化する区名")
    args = parser.parse_args()

    if args.mini_number is not None and args.mini_score is not None:
        print(normalize_mini_score_result({"mini.number": args.mini_number, "mini.score": args.mini_score}))
    elif args.anzen_ku:
        print(normalize_from_function_result(Path("score") / "anzen.py", "get_anzen_score_by_ku", args.anzen_ku))
    else:
        # 既存デモ
        values = [8.0, 5.0, 10.0]
        axis_values = [1, 2, 3]
        score_map = normalize_and_store(values, axis_values)
        print(score_map)
