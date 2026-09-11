import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification


# Path to the last successfully saved checkpoint
MODEL_PATH = "./results/checkpoint-3159"


# Load the fine-tuned model and tokenizer
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)

# Switch the model to prediction mode
model.eval()

def classify_email(subject, body):
    email_text = subject + " " + body

    inputs = tokenizer(
        email_text,
        return_tensors="pt",
        truncation=True
    )

    with torch.no_grad():
        outputs = model(**inputs)

    probabilities = torch.sigmoid(outputs.logits)[0]

    threshold = 0.2
    results = []

    for index, probability in enumerate(probabilities):
     if probability >= threshold:
        label = model.config.id2label[index]

        results.append({
            "category": label,
            "confidence": probability.item()
        })

    return results
