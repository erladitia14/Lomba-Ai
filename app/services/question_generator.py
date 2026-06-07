import random
import re
from collections import Counter

from .text_cleaner import split_sentences

STOPWORDS = {
    "yang", "dan", "di", "ke", "dari", "untuk", "dengan", "pada", "adalah", "atau",
    "dalam", "ini", "itu", "sebagai", "karena", "oleh", "akan", "dapat", "tidak",
    "lebih", "juga", "antara", "yaitu", "secara", "the", "and", "for", "with", "from",
}


def _keywords(text):
    words = re.findall(r"\b[A-Za-zÀ-ÿ]{5,}\b", text.lower())
    filtered = [word for word in words if word not in STOPWORDS]
    return [word for word, _ in Counter(filtered).most_common(40)]


def _make_question(sentence, keyword):
    blanked = re.sub(re.escape(keyword), "_____", sentence, count=1, flags=re.IGNORECASE)
    return f"Lengkapi pernyataan berikut: {blanked}"


def generate_questions(text, total=10):
    sentences = split_sentences(text)
    keywords = _keywords(text)

    if len(sentences) < 2 or len(keywords) < 4:
        return []

    questions = []
    used_sentences = set()

    for sentence in sentences:
        if len(questions) >= total:
            break

        lowered = sentence.lower()
        answer = next((word for word in keywords if word in lowered), None)

        if not answer or sentence in used_sentences:
            continue

        distractors = [word for word in keywords if word != answer and word not in lowered]
        if len(distractors) < 3:
            continue

        options = random.sample(distractors, 3) + [answer]
        random.shuffle(options)

        questions.append({
            "question": _make_question(sentence, answer),
            "options": [option.title() for option in options],
            "answer": answer.title(),
            "explanation": f"Jawaban yang tepat adalah '{answer.title()}' karena kata tersebut muncul sebagai konsep penting pada kalimat asli dari materi PDF.",
            "source": sentence,
        })
        used_sentences.add(sentence)

    return questions
