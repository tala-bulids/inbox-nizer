import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification


# Path to the last successfully saved checkpoint
MODEL_PATH = "./results/checkpoint-3159"


# Load the fine-tuned model and tokenizer
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)

# Switch the model to prediction mode
model.eval()


# Get a new email from the user
subject = input("Enter email subject: ")
body = input("Enter email body: ")

email_text = subject + " " + body


# Convert the email into tokens
inputs = tokenizer(
    email_text,
    return_tensors="pt",
    truncation=True
)


# Get model predictions
with torch.no_grad():
    outputs = model(**inputs)


# Convert logits into independent probabilities
probabilities = torch.sigmoid(outputs.logits)[0]


# Display categories above the confidence threshold
threshold = 0.5
found_category = False

print("\nPredicted categories:")

for index, probability in enumerate(probabilities):
    if probability >= threshold:
        label = model.config.id2label[index]

        print(f"- {label}: {probability.item():.2%}")
        found_category = True


if not found_category:
    print("No category passed the confidence threshold.")