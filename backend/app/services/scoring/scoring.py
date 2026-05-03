def calculate_priority_score(
    *,
    resume_match_score: float,
    verification_score: float,
    freshness_score: float,
    location_score: float,
    application_ease_score: float,
) -> float:
    score = (
        0.40 * resume_match_score
        + 0.25 * verification_score
        + 0.20 * freshness_score
        + 0.10 * location_score
        + 0.05 * application_ease_score
    )
    return round(score, 2)

