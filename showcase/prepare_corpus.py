"""Recompute authored corpus vectors offline with pinned original E5; never overwrite."""
import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('Choose a new output; never replace a release index silently')
    from huggingface_hub import snapshot_download
    spec=json.loads((ROOT/'docs/phase2/evidence/encoder-artifact-manifest.json').read_text())
    snapshot=Path(snapshot_download(spec['model'],revision=spec['revision'],local_files_only=True))
    for name,expected in spec['local_files_sha256'].items():
        with (snapshot/name.replace('\\','/')).open('rb') as stream:
            if hashlib.file_digest(stream,'sha256').hexdigest()!=expected:raise ValueError('Source encoder mismatch')
    os.environ['EMBEDDING_REVISION']=spec['revision']
    os.environ['EMBEDDING_DEVICE']='cpu'
    from embedding_service import embed_passages
    from showcase.engine import collection
    from showcase.intelligence import chunks,index_version
    passages=chunks(collection());vectors=[]
    for i in range(0,len(passages),4):
        vectors.extend(embed_passages([p['embedding_text'] for p in passages[i:i+4]]))
    result={'format':1,'collection_version':index_version(collection()),'encoder_revision':spec['revision'],
            'source_receipt_sha256':None,'chunk_ids':[p['chunk_id'] for p in passages],'vectors':vectors}
    with args.output.open('x',encoding='utf-8') as output:output.write(json.dumps(result,separators=(',',':'))+'\n')
    import numpy as np
    expected=np.asarray(json.loads((ROOT/'showcase/corpus-vectors-v1.json').read_text())['vectors'])
    print(json.dumps({'source_hashes_verified':True,'chunks':len(vectors),'max_vector_difference_from_release':float(abs(expected-np.asarray(vectors)).max()),'release_index_modified':False}))


if __name__=='__main__':main()
