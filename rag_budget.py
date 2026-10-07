"""Pack complete escaped SOURCE blocks into the actual GGUF token budget."""
import re

from rag_prompt import build_rag_messages

SAFETY_TOKENS = 32


def get_budget():
    from local_llm import get_llm_provider
    return get_llm_provider()


def pack_context(question, context, sources, budget=None):
    budget = budget if budget is not None else get_budget()
    available = budget.context_size - budget.max_new_tokens - SAFETY_TOKENS
    blocks = re.findall(r'\[SOURCE email_id=\d+ chunk=\d+\]\n.*?\n\[END SOURCE\]', context, re.DOTALL)
    packed, kept = [], []
    for block in blocks:
        candidate = '\n\n'.join(packed + [block])
        if budget.count_tokens(build_rag_messages(question, candidate)) > available:
            # Whole blocks preserve records, negations and provenance. Never slice facts.
            continue
        identity = re.match(r'\[SOURCE email_id=(\d+) chunk=(\d+)\]', block)
        matching = [s for s in sources if s['email_id'] == int(identity[1])
                    and s['chunk_index'] == int(identity[2])]
        if matching:
            packed.append(block)
            kept.extend(matching)
    messages = build_rag_messages(question, '\n\n'.join(packed))
    tokens = budget.count_tokens(messages)
    return dict(messages=messages, sources=kept,
                audit=dict(prompt_tokens=tokens, output_tokens=budget.max_new_tokens,
                           safety_tokens=SAFETY_TOKENS, context_size=budget.context_size,
                           kept_blocks=len(packed), dropped_blocks=len(blocks)-len(packed)))
