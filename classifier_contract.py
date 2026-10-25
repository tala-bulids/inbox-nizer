"""Small inference contract, independent of training dependencies."""
LABELS = ['Business', 'Customer Support', 'Events & Invitations', 'Finance & Bills',
          'Job Application', 'Newsletters', 'Personal', 'Promotions', 'Reminders',
          'Travel & Bookings']


def validate_classifier_config(config):
    try:
        mapping = {int(index): label for index, label in config.id2label.items()}
        inverse = {label: int(index) for label, index in config.label2id.items()}
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError('Classifier artifact is missing its category mapping.') from exc
    if (set(mapping) != set(range(len(LABELS))) or set(mapping.values()) != set(LABELS)
            or inverse != {label: index for index, label in mapping.items()}):
        raise ValueError('Classifier category mapping is incompatible with the product contract.')
    if getattr(config, 'problem_type', None) != 'multi_label_classification':
        raise ValueError('Classifier must declare multi_label_classification for sigmoid inference.')
    return mapping


def inference_token_limit(config, tokenizer):
    limits = [512]
    for value in (getattr(config, 'max_position_embeddings', None),
                  getattr(config, 'inbox_nizer_max_length', None),
                  getattr(tokenizer, 'model_max_length', None)):
        if isinstance(value, int) and value > 0:
            limits.append(value)
    return min(limits)
