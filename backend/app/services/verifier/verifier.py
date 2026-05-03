def verify_job_placeholder() -> dict:
    return {
        "status": "needs_manual_review",
        "verification_score": 65.0,
        "likely_closed_score": 20.0,
        "evidence": [
            "Placeholder verifier has not visited the listing yet.",
            "Later stages will inspect page availability and application state.",
        ],
    }

