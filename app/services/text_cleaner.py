import re


def clean_text(text, max_chars=12000):
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s.,;:!?()\-/%]", "", text, flags=re.UNICODE)
    return text.strip()[:max_chars]


def split_sentences(text):
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [sentence.strip() for sentence in sentences if len(sentence.strip()) >= 45]
