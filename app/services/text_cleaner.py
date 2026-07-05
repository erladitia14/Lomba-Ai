import re


def clean_text(text, max_chars=None):
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s.,;:!?()\-/%]", "", text, flags=re.UNICODE)
    text = text.strip()
    if max_chars:
        return text[:max_chars]
    return text

