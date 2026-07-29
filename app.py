from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    DataCollatorWithPadding
)

# Load dataset
dataset = load_dataset("imnim/multiclass-email-classification")


# Get all unique labels
all_labels = set()

for row in dataset["train"]:
    for label in row["labels"]:
        all_labels.add(label)

all_labels = sorted(all_labels)


# Create label mappings
label2id = {
    label: index
    for index, label in enumerate(all_labels)
}

id2label = {
    index: label
    for label, index in label2id.items()
}


# Convert label names into a multi-hot vector
def encode_labels(example):
    encoded = [0.0] * len(all_labels)

    for label in example["labels"]:
        encoded[label2id[label]] = 1.0

    return {"labels": encoded}


dataset = dataset.map(encode_labels)


# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained(
    "distilbert-base-uncased"
)


# Combine email subject and body, then tokenize
def tokenize_func(example):
    text = example["subject"] + " " + example["body"]

    return tokenizer(
        text,
        truncation=True
    )


tokenized_dataset = dataset.map(
    tokenize_func,
    remove_columns=["subject", "body"]
)

# Use only the first 100 emails for testing
small_train_dataset = tokenized_dataset["train"].select(range(100))

# Dynamic padding
data_collator = DataCollatorWithPadding(
    tokenizer=tokenizer
)


# Load multi-label classification model
model = AutoModelForSequenceClassification.from_pretrained(
    "distilbert-base-uncased",
    num_labels=len(all_labels),
    problem_type="multi_label_classification",
    label2id=label2id,
    id2label=id2label
)


# Training settings
training_args = TrainingArguments(
    output_dir="./results",
    num_train_epochs=3,
    per_device_train_batch_size=2,
    save_strategy="no"
)

# Create trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset["train"],
    data_collator=data_collator
   )


# Start fine-tuning
trainer.train()
model.save_pretrained("./email_classifier")

tokenizer.save_pretrained("./email_classifier")