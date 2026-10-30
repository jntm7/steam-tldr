import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# Pretrained sentiment model, how much text it reads, and how many texts per batch
MODEL_NAME = "distilbert/distilbert-base-uncased-finetuned-sst-2-english"
MAX_TOKENS = 256
BATCH_SIZE = 32

# Use the Apple GPU when there is one
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"

# Pretrained transformer with the same predict / predict_proba interface as the baseline
class TransformerSentiment:
    def __init__(self, model_name: str = MODEL_NAME):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name).to(DEVICE).eval()
        self.positive_index = self.model.config.label2id.get("POSITIVE", 1)

    def predict_proba(self, texts) -> np.ndarray:
        texts = [str(t) for t in texts]
        positive = []
        for start in range(0, len(texts), BATCH_SIZE):
            batch = self.tokenizer(texts[start:start + BATCH_SIZE], truncation=True, max_length=MAX_TOKENS,
                                   padding=True, return_tensors="pt").to(DEVICE)
            with torch.no_grad():
                probs = torch.softmax(self.model(**batch).logits, dim=-1)
            positive.extend(probs[:, self.positive_index].cpu().tolist())
        positive = np.array(positive)
        return np.column_stack([1 - positive, positive])

    def predict(self, texts) -> np.ndarray:
        return self.predict_proba(texts)[:, 1] >= 0.5
