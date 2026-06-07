# Hazza LearnAI

Website Flask untuk mengubah PDF materi belajar menjadi latihan soal pilihan ganda.

## Fitur MVP

- Tanpa login.
- Tanpa API AI eksternal.
- Upload PDF maksimal 10 MB.
- Ekstraksi teks PDF dengan `pypdf`.
- Generator soal lokal/rule-based.
- Quiz pilihan ganda.
- Halaman hasil dan pembahasan.
- Penyimpanan session quiz dengan SQLite.

## Cara Menjalankan

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Buka browser ke:

```text
http://127.0.0.1:5000
```

## Catatan

PDF harus berisi teks yang bisa diseleksi. PDF hasil scan gambar belum didukung karena belum memakai OCR.
