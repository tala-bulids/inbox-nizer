from threading import Lock
from email_utils import clean_email_body
from classifier_contract import inference_token_limit, validate_classifier_config
from classifier_config import model_path


# Load the model.
MODEL_PATH = model_path()


tokenizer = None
model = None
_load_lock = Lock()
_inference_lock = Lock()


def load_classifier(path):
    """Load a complete local artifact; never download or silently use a base head."""
    from transformers import AutoConfig, AutoTokenizer, AutoModelForSequenceClassification

    path = model_path(path)
    if not path.is_dir():
        raise FileNotFoundError(
            'Classifier artifact is missing. Train with app.py or set EMAIL_MODEL_PATH '
            'to a directory containing config, weights and tokenizer files.'
        )
    config = AutoConfig.from_pretrained(path, local_files_only=True)
    validate_classifier_config(config)
    loaded_tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
    loaded_model, info = AutoModelForSequenceClassification.from_pretrained(
        path, local_files_only=True, output_loading_info=True
    )
    if info.get('missing_keys') or info.get('mismatched_keys') or info.get('error_msgs'):
        raise ValueError('Classifier artifact has missing or incompatible model weights.')
    loaded_model.eval()
    return loaded_tokenizer, loaded_model


def _get_classifier():
    """Publish both objects only after validating a complete local artifact."""
    global tokenizer, model
    if model is None or tokenizer is None:
        with _load_lock:
            if model is None or tokenizer is None:
                loaded_tokenizer, loaded_model = load_classifier(MODEL_PATH)
                tokenizer, model = loaded_tokenizer, loaded_model
    return tokenizer, model

def classify_email(subject, body):
    classifier_tokenizer, classifier_model = _get_classifier()
    with _inference_lock:
        return predict_with_classifier(classifier_tokenizer, classifier_model, subject, body)


def predict_with_classifier(classifier_tokenizer, classifier_model, subject, body):
    """Use identical preprocessing, limits and score semantics in API and evaluation."""
    import torch

    label_mapping = validate_classifier_config(classifier_model.config)
    max_length = inference_token_limit(classifier_model.config, classifier_tokenizer)
    email_text = ((subject or '').strip() + " " + clean_email_body(body or '')).strip()

    # One bounded CPU inference per process avoids sync workers competing for
    # full model activations. Loading is lazy so login/list/search need no model.
    with torch.inference_mode():
        inputs = classifier_tokenizer(
            email_text,
            return_tensors="pt",
            truncation=True,
            max_length=max_length,
        )
        outputs = classifier_model(**inputs)

    probabilities = torch.sigmoid(outputs.logits)[0]
    if probabilities.numel() != len(label_mapping) or not torch.isfinite(probabilities).all():
        raise RuntimeError('Classifier returned invalid category scores.')

    # Return the best match.
    index = probabilities.argmax().item()
    return [{
        "category": label_mapping[index],
        "confidence": probabilities[index].item()
    }]


def main():
    import argparse
    import json
    parser = argparse.ArgumentParser(description='Classify one email with inbox-nizer.')
    parser.add_argument('--model', help='Local artifact directory; defaults to EMAIL_MODEL_PATH.')
    parser.add_argument('--subject', default='')
    parser.add_argument('--body', default='')
    args = parser.parse_args()
    if not (args.subject.strip() or clean_email_body(args.body).strip()):
        parser.error('Provide a nonempty --subject or --body.')
    classifier_tokenizer, classifier_model = load_classifier(model_path(args.model))
    print(json.dumps(predict_with_classifier(classifier_tokenizer, classifier_model,
                                           args.subject, args.body), ensure_ascii=False))


if __name__ == '__main__':
    main()
