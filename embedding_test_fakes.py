"""Deterministic test doubles, never used by application code."""
import re
import numpy as np


class FakeTokenizer:
    def __call__(self, text, **kwargs):
        spans = [(match.start(), match.end()) for match in re.finditer(r'\S+', text)]
        return {'input_ids': list(range(len(spans))), 'offset_mapping': spans}

    def encode(self, text, add_special_tokens=True):
        count = len(self(text)['input_ids']) + (2 if add_special_tokens else 0)
        return list(range(count))


class FakeEncoder:
    def __init__(self):
        self.tokenizer = FakeTokenizer()
        self.calls = []

    def encode(self, texts, **kwargs):
        self.calls.append((list(texts), kwargs))
        vectors = []
        for text in texts:
            value = text.casefold()
            vector = np.zeros(384, dtype=np.float32)
            if any(word in value for word in ['flight', 'travel', 'جدة', 'لجدة', 'رحلة', 'سفرتي']):
                vector[0] = 1
            elif any(word in value for word in ['invoice', 'فاتورة']):
                vector[1] = 1
            else:
                vector[2] = 1
            vectors.append(vector)
        return np.asarray(vectors)
