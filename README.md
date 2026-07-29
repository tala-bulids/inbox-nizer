# Email Classification Fine-Tuning

A text classification project built with Hugging Face Transformers and PyTorch.

This project fine-tunes DistilBERT on a real email dataset to classify emails into multiple categories.

## Features

- Fine-tune DistilBERT for email classification
- Multi-label classification
- Hugging Face Trainer API
- Predict categories for new emails
- Save and load trained checkpoints

## Categories

- Business
- Customer Support
- Events & Invitations
- Finance & Bills
- Job Application
- Newsletters
- Personal
- Promotions
- Reminders
- Travel & Bookings

## Project Structure

```
text-classification-finetuning/
│
├── app.py                 # Training script
├── predict.py             # Predict new emails
├── requirements.txt
├── .gitignore
├── results/
└── README.md
```

## Dataset

This project uses the **imnim/multiclass-email-classification** dataset from Hugging Face.

The dataset contains over 2,000 labeled emails with 10 categories.

## Installation

```bash
git clone https://github.com/your-username/text-classification-finetuning.git

cd text-classification-finetuning

python -m venv env

env\Scripts\activate

pip install -r requirements.txt
```

## Train the Model

```bash
python app.py
```

## Predict

```bash
python predict.py
```

Example:

```
Subject:
Payment reminder

Body:
Your monthly invoice is ready. Please complete the payment before Friday.
```

Output:

```
Finance & Bills
```

## Technologies

- Python
- Hugging Face Transformers
- PyTorch
- Datasets
- Accelerate

## What I Learned

- Fine-tuning pretrained language models
- Multi-label text classification
- Hugging Face Trainer
- Tokenization
- Data preprocessing
- Saving and loading checkpoints