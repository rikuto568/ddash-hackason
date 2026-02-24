
def weighted_score(scores: list[float], weights: list[int]) -> float:
    if len(scores) != len(weights):
        raise ValueError("scores と weights の要素数は同じにしてください。")
    if not scores:
        raise ValueError("scores が空です。")

    total_weight = sum(weights)
    if total_weight <= 0:
        raise ValueError("weights の合計は 1 以上にしてください。")

    return sum(score * weight for score, weight in zip(scores, weights)) / total_weight


if __name__ == "__main__":
    SCORE_1 = 100
    SCORE_2 = 20
    SCORE_3 = 30

    WEIGHT_1 = 5
    WEIGHT_2 = 4
    WEIGHT_3 = 3

    scores = [SCORE_1, SCORE_2, SCORE_3]
    weights = [WEIGHT_1, WEIGHT_2, WEIGHT_3]

    result = weighted_score(scores, weights)
    print(f"点数: {result:.2f}")
