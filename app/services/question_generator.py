import json
import random
import re
from collections import Counter
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import current_app

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


def _local_generate_questions(text, total=10):
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


def _extract_json_object(content):
    content = content.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", content, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        content = fenced.group(1).strip()

    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or start >= end:
        raise ValueError("AI response does not contain a JSON object")

    return json.loads(content[start:end + 1])


def _normalize_ai_questions(payload, total):
    raw_questions = payload.get("questions") if isinstance(payload, dict) else None
    if not isinstance(raw_questions, list):
        raise ValueError("AI response JSON must contain a questions array")

    questions = []
    for item in raw_questions:
        if not isinstance(item, dict):
            continue

        question = str(item.get("question", "")).strip()
        options = item.get("options", [])
        answer = str(item.get("answer", "")).strip()
        explanation = str(item.get("explanation", "")).strip()
        source = str(item.get("source", "")).strip()

        if not question or not isinstance(options, list) or len(options) != 4 or not answer:
            continue

        clean_options = [str(option).strip() for option in options if str(option).strip()]
        if len(clean_options) != 4 or answer not in clean_options:
            continue

        questions.append({
            "question": question,
            "options": clean_options,
            "answer": answer,
            "explanation": explanation or f"Jawaban yang tepat adalah {answer}.",
            "source": source,
        })

        if len(questions) >= total:
            break

    return questions


def _generate_questions_with_9router(text, total):
    base_url = current_app.config["NINE_ROUTER_BASE_URL"].rstrip("/")
    model = current_app.config["NINE_ROUTER_MODEL"]
    api_key = current_app.config.get("NINE_ROUTER_API_KEY", "")
    timeout = current_app.config.get("NINE_ROUTER_TIMEOUT", 120)

    material = text[: current_app.config.get("NINE_ROUTER_MAX_INPUT_CHARS", 14000)]
    prompt = f"""
Buat {total} soal pilihan ganda berkualitas dari materi PDF berikut.

Aturan wajib:
- Bahasa Indonesia.
- Setiap soal punya tepat 4 opsi jawaban.
- Jawaban benar harus sama persis dengan salah satu opsi.
- Distraktor harus masuk akal dan tidak terlalu mudah ditebak.
- Explanation singkat menjelaskan alasan jawaban benar.
- Source berisi potongan kalimat/paragraf pendukung dari materi.
- Jangan menambah teks di luar JSON.

Format JSON wajib:
{{
  "questions": [
    {{
      "question": "...",
      "options": ["A", "B", "C", "D"],
      "answer": "A",
      "explanation": "...",
      "source": "..."
    }}
  ]
}}

Materi PDF:
{material}
""".strip()

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Kamu adalah pembuat soal edukasi yang akurat dan disiplin menghasilkan JSON valid."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 4000,
    }

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    request = Request(
        f"{base_url}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            response_text = response.read().decode("utf-8")
            response_payload = _parse_9router_response(response_text)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"9Router HTTP {exc.code}: {detail[:500]}") from exc
    except URLError as exc:
        raise RuntimeError(f"9Router connection failed: {exc.reason}") from exc

    content = response_payload["choices"][0]["message"]["content"]
    return _normalize_ai_questions(_extract_json_object(content), total)


def _parse_9router_response(response_text):
    response_text = response_text.strip()
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    # 9Router can return one JSON object followed by SSE markers like data: [DONE].
    for line in response_text.splitlines():
        line = line.strip()
        if not line or line == "data: [DONE]":
            continue
        if line.startswith("data: "):
            line = line[6:].strip()
        if line.startswith("{"):
            return json.loads(line)

    raise ValueError("9Router response is not valid JSON")


def generate_questions(text, total=10):
    if current_app.config.get("NINE_ROUTER_ENABLED", True):
        try:
            questions = _generate_questions_with_9router(text, total)
            if questions:
                return questions
            raise RuntimeError("9Router returned no valid questions")
        except Exception as exc:
            if not current_app.config.get("NINE_ROUTER_FALLBACK_ENABLED", False):
                raise
            current_app.logger.warning("9Router question generation failed, using local fallback: %s", exc)

    return _local_generate_questions(text, total)
