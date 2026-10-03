"""Offline GGUF generation; explicit setup is the only download step."""

import os
import re
from pathlib import Path
from threading import Lock

DEFAULT_MODEL_PATH = Path(__file__).parent / 'local_models' / 'Qwen3-0.6B-Q4_K_M.gguf'


class ProviderUnavailable(RuntimeError):
    pass


class ContextTooLarge(ValueError):
    pass


def _integer(name, default, minimum, maximum):
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        raise ProviderUnavailable(f'{name} must be an integer.') from None
    if not minimum <= value <= maximum:
        raise ProviderUnavailable(f'{name} must be between {minimum} and {maximum}.')
    return value


def _create_backend(**kwargs):
    from llama_cpp import Llama
    return Llama(**kwargs)


def _qwen_prompt(messages):
    # Qwen3 non-thinking ChatML, without tools.
    parts = []
    for message in messages:
        if message['role'] not in ('system', 'user', 'assistant'):
            raise ProviderUnavailable('Unsupported local chat message role.')
        content = message['content'].replace('<|', '&lt;|')
        parts.append(f"<|im_start|>{message['role']}\n{content}<|im_end|>\n")
    return ''.join(parts) + '<|im_start|>assistant\n<think>\n\n</think>\n\n'


class LocalLLM:
    def __init__(self):
        self.model_path = Path(os.getenv('RAG_MODEL_PATH', str(DEFAULT_MODEL_PATH))).expanduser()
        self.max_new_tokens = _integer('RAG_MAX_NEW_TOKENS', 256, 32, 1024)
        self.context_size = _integer('RAG_CONTEXT_SIZE', 2048, 512, 8192)
        self.threads = _integer('RAG_THREADS', min(2, os.cpu_count() or 1), 1, 32)
        if self.max_new_tokens >= self.context_size:
            raise ProviderUnavailable('RAG_MAX_NEW_TOKENS must be smaller than RAG_CONTEXT_SIZE.')
        self._model = None
        self._lock = Lock()

    def _load(self):
        if self._model is not None:
            return
        if not self.model_path.is_file() or self.model_path.stat().st_size == 0:
            raise ProviderUnavailable('GGUF model missing or empty. Run download_rag_model.py or set RAG_MODEL_PATH.')
        try:
            self._model = _create_backend(
                model_path=str(self.model_path), n_gpu_layers=0,
                n_ctx=self.context_size, n_batch=64, n_ubatch=64,
                n_threads=self.threads, n_threads_batch=self.threads,
                use_mmap=True, use_mlock=False, seed=0, verbose=False,
            )
        except Exception:
            raise ProviderUnavailable('Cannot initialize GGUF backend. Check the CPU wheel, model compatibility and available RAM.') from None

    def generate(self, messages: list[dict[str, str]]) -> str:
        with self._lock:
            self._load()
            try:
                tokens = self._model.tokenize(_qwen_prompt(messages).encode('utf-8'), add_bos=False, special=True)
                if len(tokens) + self.max_new_tokens > self.context_size:
                    raise ContextTooLarge('Question and sources exceed RAG_CONTEXT_SIZE; reduce chunk_limit or max_context_chars.')
                result = self._model.create_completion(
                    prompt=tokens, max_tokens=self.max_new_tokens,
                    temperature=0.0, seed=0, stream=False,
                    stop=['<|im_end|>', '<|endoftext|>'],
                )
                answer = result['choices'][0]['text']
                if not isinstance(answer, str):
                    raise ValueError('Invalid backend result')
                # Suppress tagged reasoning, including incomplete output.
                answer = re.sub(r'<think>.*?</think>', '', answer, flags=re.DOTALL | re.IGNORECASE)
                if re.search(r'</?think\b', answer, re.IGNORECASE):
                    raise ValueError('Incomplete reasoning output')
                return answer.strip()
            except (ContextTooLarge, ProviderUnavailable):
                raise
            except Exception:
                raise ProviderUnavailable('Local generation failed; check model compatibility and available RAM.') from None


_provider = None
_provider_lock = Lock()


def get_llm_provider():
    global _provider
    with _provider_lock:
        if os.getenv('RAG_PROVIDER', 'local') != 'local':
            raise ProviderUnavailable('Unsupported RAG_PROVIDER. Currently supported: local.')
        if _provider is None:
            _provider = LocalLLM()
        return _provider
