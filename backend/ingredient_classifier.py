# ingredient_classifier.py (локальная загрузка, без интернета)
"""Семантический фильтр ингредиентов на основе дообученной ModernBERT-base (локально)."""
import os
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

LOCAL_MODEL_PATH = os.path.join(os.path.dirname(__file__), "ingredient_classifier")
_tokenizer = None
_model = None
_device = None

def load_model():
    global _tokenizer, _model, _device
    if _model is not None:
        return
    _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[NLP] Завантаження моделі з локальної папки {LOCAL_MODEL_PATH} на {_device}...")
    _tokenizer = AutoTokenizer.from_pretrained(LOCAL_MODEL_PATH)
    _model = AutoModelForSequenceClassification.from_pretrained(
        LOCAL_MODEL_PATH, num_labels=2, ignore_mismatched_sizes=True
    )
    _model.to(_device)
    _model.eval()
    print("[NLP] Модель готова.")

def is_ingredient(text: str) -> bool:
    """Повертає True, якщо текст схожий на назву інгредієнта."""
    load_model()
    inputs = _tokenizer(text, return_tensors="pt", truncation=True, max_length=64)
    inputs = {k: v.to(_device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = _model(**inputs)
        probs = torch.softmax(outputs.logits, dim=1)
        score = probs[0, 1].item()
    return score > 0.6