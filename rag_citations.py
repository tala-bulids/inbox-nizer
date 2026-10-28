"""Pure citation syntax validation shared by Gmail RAG and the AI showcase."""
import re
from llm_provider import InvalidGeneration


def validate_citations(answer, sources):
    pattern = r'\[email_id=(\d+)\]'
    cited = list(dict.fromkeys(int(value) for value in re.findall(pattern, answer)))
    allowed = {source['email_id'] for source in sources}
    if (not cited or not set(cited) <= allowed
            or any(not re.search(pattern, paragraph) for paragraph in answer.split('\n') if paragraph.strip())
            or '[email_id' in re.sub(pattern, '', answer)):
        raise InvalidGeneration('Generation failed source citation validation')
    return cited
