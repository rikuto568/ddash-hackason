from __future__ import annotations

from typing import Sequence

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

try:
    import calculateseg
except ImportError:  # /weighted only usage can work without calculateseg.py
    calculateseg = None


app = FastAPI()


class ScoreRequest(BaseModel):
    # 既存互換: values + axis_values から内部で正規化して使う
    values: list[float]
    axis_values: list[int]
    weights: list[float] | None = None


class WeightedScoresRequest(BaseModel):
    # 新規: 正規化済み score をそのまま受け取って加重平均する
    scores: list[float]
    weights: list[float]


def weighted_score(scores: Sequence[float], weights: Sequence[float]) -> float:
    # 数式は変更しない（加重平均）
    if len(scores) != len(weights):
        raise ValueError("scores and weights must have the same length")
    if not scores:
        raise ValueError("scores is empty")

    total_weight = sum(weights)
    if total_weight <= 0:
        raise ValueError("sum(weights) must be greater than 0")

    return sum(score * weight for score, weight in zip(scores, weights)) / total_weight


def build_scores_from_normalized(
    values: Sequence[float], axis_values: Sequence[int]
) -> tuple[list[float], dict[str, float]]:
    """
    calculateseg.py で正規化し、FastAPIで使いやすい形にする
    - scores: [SCORE_1, SCORE_2, ...] のリスト
    - score_map: {"SCORE_1": ..., "SCORE_2": ...}
    """
    if calculateseg is None:
        raise RuntimeError("calculateseg.py is required for /result (normalize_then_weighted mode)")
    score_map = calculateseg.normalize_and_store(values, axis_values)
    scores = calculateseg.get_score_list()
    return scores, score_map


@app.get("/")
def root():
    return {"message": "Server OK"}


@app.get("/result/sample")
def get_result_sample():
    """
    既存サンプル:
    values -> 内部正規化 -> 加重平均
    """
    values = [8.0, 5.0, 10.0]
    axis_values = [1, 2, 3]
    weights = [5, 4, 3]

    try:
        scores, score_map = build_scores_from_normalized(values, axis_values)
        result = weighted_score(scores, weights)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "mode": "normalize_then_weighted",
        "values": values,
        "axis_values": axis_values,
        "normalized_score_map": score_map,
        "scores": scores,
        "weights": weights,
        "weighted_result": round(result * 100, 4),
    }


@app.get("/weighted/sample")
def get_weighted_sample():
    """
    新サンプル:
    正規化済みスコアを直接受けて加重平均
    """
    scores = [0.3, 0.6]
    weights = [5, 3]
    try:
        result = weighted_score(scores, weights)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "mode": "weighted_only",
        "scores": scores,
        "weights": weights,
        "weighted_result": round(result * 100, 4),
    }


@app.post("/result")
def get_result(payload: ScoreRequest):
    """
    既存互換API:
    - values: 元の値
    - axis_values: 正規化の軸値（axis * 10 の axis）
    - weights: 任意（ある場合だけ加重平均）
    """
    try:
        scores, score_map = build_scores_from_normalized(payload.values, payload.axis_values)

        response: dict[str, object] = {
            "mode": "normalize_then_weighted",
            "normalized_score_map": score_map,
            "scores": scores,
        }

        if payload.weights is not None:
            response["weights"] = payload.weights
            response["weighted_result"] = round(weighted_score(scores, payload.weights) * 100, 4)

        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/weighted")
def get_weighted_from_scores(payload: WeightedScoresRequest):
    """
    新API（推奨）:
    seikika.py などで正規化済みの scores を受け取り、加重平均だけを行う
    """
    try:
        return {
            "mode": "weighted_only",
            "scores": payload.scores,
            "weights": payload.weights,
            "weighted_result": round(weighted_score(payload.scores, payload.weights) * 100, 4),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    # ローカル確認用
    print(get_result_sample())
    print(get_weighted_sample())
