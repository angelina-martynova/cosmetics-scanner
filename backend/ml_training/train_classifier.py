# train_classifier.py (FINAL)
"""Обучение классификатора ингредиентов на основе локальной ModernBERT-base."""
import os
import torch
import pandas as pd
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    DataCollatorWithPadding,
)
from datasets import Dataset
from sklearn.metrics import accuracy_score

LOCAL_MODEL_PATH = "./ingredient_classifier"
OUTPUT_DIR = "./ingredient_classifier"

def is_valid(example):
    text = example.get("text")
    return text is not None and text.strip() != ""

# 1. Загрузка данных
df = pd.read_csv("train.csv")
dataset = Dataset.from_pandas(df)
dataset = dataset.filter(is_valid)

# 2. Токенизация
tokenizer = AutoTokenizer.from_pretrained(LOCAL_MODEL_PATH)
def tokenize(example):
    text = example["text"] or ""
    return tokenizer(text, truncation=True, max_length=64)
dataset = dataset.map(tokenize)
dataset = dataset.train_test_split(test_size=0.1, seed=42)

# 3. Модель (классификационная голова инициализируется случайно)
model = AutoModelForSequenceClassification.from_pretrained(
    LOCAL_MODEL_PATH, num_labels=2, ignore_mismatched_sizes=True
)

# 4. Аргументы обучения
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=5,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=16,
    logging_steps=20,
    eval_strategy="steps",
    save_strategy="steps",
    save_steps=200,
    load_best_model_at_end=True,
    metric_for_best_model="accuracy",
    report_to="none",
)

# 5. Метрика
def compute_metrics(pred):
    labels = pred.label_ids
    preds = pred.predictions.argmax(-1)
    return {"accuracy": accuracy_score(labels, preds)}

# 6. Коллатор для динамического паддинга
data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

# 7. Тренер
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset["train"],
    eval_dataset=dataset["test"],
    compute_metrics=compute_metrics,
    data_collator=data_collator,
)

# 8. Обучение
trainer.train()

# 9. Сохранение в обход safetensors (Windows fix)
os.makedirs(OUTPUT_DIR, exist_ok=True)
torch.save(model.state_dict(), os.path.join(OUTPUT_DIR, "pytorch_model.bin"))
model.config.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
print(f"Дообученная модель сохранена в {OUTPUT_DIR}")