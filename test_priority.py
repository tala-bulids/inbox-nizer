from priority import calculate_priority


def test_high_priority_email():
    predictions = [
        {
            "category": "Travel & Bookings",
            "confidence": 0.99
        }
    ]

    result = calculate_priority(predictions)

    assert result["priority_score"] == 0.7425
    assert result["priority_level"] == "high"


def test_medium_priority_email():
    predictions = [
        {
            "category": "Business",
            "confidence": 0.8
        }
    ]

    result = calculate_priority(predictions)

    assert result["priority_score"] == 0.48
    assert result["priority_level"] == "medium"


def test_low_priority_email():
    predictions = [
        {
            "category": "Promotions",
            "confidence": 0.9
        }
    ]

    result = calculate_priority(predictions)

    assert result["priority_score"] == 0.18
    assert result["priority_level"] == "low"


def test_no_predictions():
    result = calculate_priority([])

    assert result["priority_score"] == 0.5
    assert result["priority_level"] == "medium"


def test_multiple_predictions_uses_highest_priority():
    predictions = [
        {
            "category": "Newsletters",
            "confidence": 0.9
        },
        {
            "category": "Finance & Bills",
            "confidence": 0.8
        }
    ]

    result = calculate_priority(predictions)

    assert result["priority_score"] == 0.68
    assert result["priority_level"] == "high"