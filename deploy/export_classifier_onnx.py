"""Export existing validated classifier weights offline; never train/download.

Run from the repository root with export-only torch/transformers/onnx dependencies.
The output belongs outside Git. Compare outputs before provisioning the artifact.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import torch
    import numpy as np
    import onnx
    from predict import load_classifier
    tokenizer, model = load_classifier(args.source)
    torch.set_num_threads(1)
    model.set_attn_implementation('eager')
    args.output.mkdir(parents=True, exist_ok=False)
    tokenizer.save_pretrained(args.output)
    model.config.save_pretrained(args.output)

    class Export(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.model = model

        def forward(self, input_ids, attention_mask):
            return self.model(input_ids=input_ids, attention_mask=attention_mask).logits

    sample = tokenizer('Synthetic invoice payment due Friday.', return_tensors='pt')
    texts = ['Your invoice is due Friday.', 'يرجى سداد الفاتورة يوم الجمعة.',
             'Please attend the team meeting.', 'يرجى حضور اجتماع الفريق.',
             'Your job application was received.', 'تم استلام طلب التوظيف.',
             'Your flight leaves at 09:00.', 'تغادر رحلتك الساعة التاسعة.',
             'Please reset your account password.', 'يرجى إعادة تعيين كلمة المرور.']
    references = []
    with torch.inference_mode():
        for value in texts:
            references.append(model(**tokenizer(value, return_tensors='pt', truncation=True, max_length=512)).logits.numpy()[0])
    np.save(args.output / 'reference.npy', np.asarray(references))
    (args.output / 'probe_texts.json').write_text(json.dumps(texts, ensure_ascii=False), encoding='utf-8')
    fp32 = args.output / 'model.onnx'
    with torch.inference_mode():
        torch.onnx.export(Export().eval(), (sample['input_ids'], sample['attention_mask']), str(fp32),
            input_names=['input_ids', 'attention_mask'], output_names=['logits'],
            dynamic_axes={'input_ids': {0:'batch', 1:'sequence'}, 'attention_mask': {0:'batch', 1:'sequence'},
                          'logits': {0:'batch'}}, opset_version=17, dynamo=False)
    # Preserve FP32 weights exactly while allowing ORT to map external tensors
    # without a second full copy of the weights in its protobuf buffer.
    graph = onnx.load(fp32)
    onnx.save_model(graph, fp32, save_as_external_data=True, all_tensors_to_one_file=True,
                    location='weights.bin', size_threshold=1024)
    # No paths, training data or personal text in the deployable provenance record.
    def sha(path):
        with path.open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest()
    source = Path(args.source)
    manifest = {p.name: sha(p) for p in source.iterdir() if p.suffix == '.safetensors' or p.name == 'config.json'}
    (args.output / 'source-sha256.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
