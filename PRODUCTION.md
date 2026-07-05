# Production Gemini Setup

Tujuan production: website bisa diakses semua orang, tetapi API key Gemini tetap hanya ada di server Flask.

## 1. Siapkan API Key Gemini

1. Buka Google AI Studio.
2. Buat API key untuk Gemini API.
3. Simpan key tersebut hanya di environment server Flask.

Jangan hardcode API key ke repository dan jangan kirim API key ke JavaScript/frontend.

## 2. Environment Production Flask

Set environment variables di server hosting Flask:

```env
GEMINI_ENABLED=true
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-1.5-flash
GEMINI_FALLBACK_ENABLED=false
GEMINI_TIMEOUT=180
GEMINI_MAX_INPUT_CHARS=24000
```

Jika deploy memakai `.env`, isi file `.env` di server production saja. Jangan commit `.env` ke git.

## 3. Test dari Server Production

Jalankan dari server Flask:

```bash
python - <<'PY'
from app import create_app
from app.services.question_generator import generate_questions

app = create_app()
text = 'Fotosintesis adalah proses tumbuhan membuat makanan dengan bantuan cahaya matahari. Klorofil menyerap energi cahaya. Oksigen dilepaskan sebagai hasil proses.' * 10
with app.app_context():
    print(app.config['GEMINI_MODEL'])
    print(generate_questions(text, total=1)[0]['question'])
PY
```

Jika muncul error `GEMINI_API_KEY is not configured`, berarti `GEMINI_API_KEY` belum terbaca. Jika muncul error authorization dari Gemini, buat API key baru dari Google AI Studio dan update environment production.

## 4. Kenapa API Key Tidak Diletakkan di Frontend?

Aplikasi Flask memanggil Gemini dari backend, sehingga user publik bisa memakai website tanpa melihat API key. API key tetap aman di server dan tidak pernah dikirim ke browser user.
