"""Offline qualification adapter, reusing the existing compact XLM tokenizer.

This is not a production backend selection. The graph's parity, provenance and
capacity must be measured before adopting an export. No classifier replacement.
"""
from pathlib import Path
import re
import numpy as np

class XlmTokenizer:
    """SentencePiece with the existing XLM-R special-token IDs and offsets."""
    model_max_length = 512
    _special = {'<s>': 0, '<pad>': 1, '</s>': 2, '<unk>': 3, '<mask>': 250001}
    _pattern = re.compile(r'<s>|<pad>|</s>|<unk>|<mask>')

    def __init__(self, path):
        import sentencepiece as spm
        self.processor = spm.SentencePieceProcessor(model_file=str(path))
        if self.processor.get_piece_size() != 250000:
            raise ValueError('Unexpected multilingual E5 vocabulary')

    def _pieces(self, text):
        ids, offsets = [], []
        cursor = 0

        def ordinary(start, end):
            segment = text[start:end]
            # SentencePiece protobuf offsets are UTF-8 bytes; chunking slices
            # Python Unicode strings. Convert boundaries before exposing them.
            byte_to_char = []
            for index, char in enumerate(segment):
                byte_to_char.extend([index] * len(char.encode('utf-8')))
            byte_to_char.append(len(segment))
            for piece in self.processor.encode(segment, return_type='proto').pieces:
                ids.append(piece.id + 1 if piece.id else 3)
                begin, finish = byte_to_char[piece.begin], byte_to_char[piece.end]
                while begin < finish and segment[begin].isspace():
                    begin += 1
                if begin == finish and begin < len(segment):
                    finish += 1
                offsets.append((start + begin, start + finish))

        for match in self._pattern.finditer(text):
            end = match.start()
            if match.group() == '<mask>':
                while end > cursor and text[end - 1].isspace():
                    end -= 1
            ordinary(cursor, end)
            ids.append(self._special[match.group()])
            offsets.append((end, match.end()))
            cursor = match.end()
        ordinary(cursor, len(text))
        return ids, offsets

    def encode(self, text, add_special_tokens=True):
        ids, _ = self._pieces(text)
        return [0, *ids, 2] if add_special_tokens else ids

    def __call__(self, text, *, add_special_tokens=True, truncation=False,
                 return_offsets_mapping=False, max_length=512):
        ids, offsets = self._pieces(text)
        if truncation:
            size = max_length - (2 if add_special_tokens else 0)
            ids, offsets = ids[:size], offsets[:size]
        if add_special_tokens:
            ids, offsets = [0, *ids, 2], [(0, 0), *offsets, (0, 0)]
        result = {'input_ids': ids, 'attention_mask': [1] * len(ids)}
        if return_offsets_mapping:
            result['offset_mapping'] = offsets
        return result


class ProbeEncoder:
    def __init__(self, directory, filename):
        import onnxruntime as ort
        self.tokenizer = XlmTokenizer(Path(directory) / 'sentencepiece.bpe.model')
        options = ort.SessionOptions()
        options.intra_op_num_threads = options.inter_op_num_threads = 1
        options.enable_cpu_mem_arena = options.enable_mem_pattern = False
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
        self.session = ort.InferenceSession(str(Path(directory) / filename), options,
                                            providers=['CPUExecutionProvider'])

    def encode(self, inputs, **kwargs):
        rows=[]
        for text in inputs:
            ids=self.tokenizer.encode(text)
            if not 1 <= len(ids) <= 512:
                raise ValueError('Input exceeds reviewed token budget')
            values=self.session.run(None, {'input_ids':np.asarray([ids],dtype=np.int64),
                'attention_mask':np.ones((1,len(ids)),dtype=np.int64)})[0][0]
            if values.shape != (384,) or not np.isfinite(values).all():
                raise ValueError('Invalid embedding contract')
            rows.append(values)
        return np.asarray(rows)
