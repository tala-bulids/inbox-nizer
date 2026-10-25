HIGH_PRIORITY_CATEGORIES = {
    "Finance & Bills": 0.85,
    "Job Application": 0.85,
    "Reminders": 0.80,
    "Travel & Bookings": 0.75,
}

MEDIUM_PRIORITY_CATEGORIES = {
    "Customer Support": 0.65,
    "Business": 0.60,
    "Events & Invitations": 0.55,
    "Personal": 0.50,
}

LOW_PRIORITY_CATEGORIES = {
    "Newsletters": 0.30,
    "Promotions": 0.20,
}


def calculate_priority(predictions):
    if not predictions:
        return {
            "priority_score": 0.5,
            "priority_level": "medium"
        }

    scores = []

    for prediction in predictions:
        category = prediction["category"]
        confidence = prediction["confidence"]

        if category in HIGH_PRIORITY_CATEGORIES:
            base_score = HIGH_PRIORITY_CATEGORIES[category]

        elif category in MEDIUM_PRIORITY_CATEGORIES:
            base_score = MEDIUM_PRIORITY_CATEGORIES[category]

        else:
            base_score = LOW_PRIORITY_CATEGORIES.get(
                category,
                0.5
            )

        weighted_score = base_score * confidence
        scores.append(weighted_score)

    priority_score = max(scores)

    if priority_score >= 0.65:
        priority_level = "high"

    elif priority_score >= 0.35:
        priority_level = "medium"

    else:
        priority_level = "low"

    return {
        "priority_score": round(priority_score, 4),
        "priority_level": priority_level
    }