"""Test embedding model loading and inference."""
import time
import os

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

print('Starting model load test...')
start = time.time()
try:
    from sentence_transformers import SentenceTransformer
    print(f'Import took {time.time()-start:.1f}s')
    print('Loading model...')
    m = SentenceTransformer('BAAI/bge-small-zh-v1.5', local_files_only=True)
    print(f'Model loaded in {time.time()-start:.1f}s')
    print('Encoding test...')
    vec = m.encode(['测试文本'], normalize_embeddings=True, show_progress_bar=False)
    print(f'Encoded in {time.time()-start:.1f}s, shape: {vec.shape}')
    print('SUCCESS')
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
