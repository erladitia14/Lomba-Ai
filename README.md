# Hazza LearnAI

Website Flask untuk mengubah PDF materi belajar menjadi latihan soal pilihan ganda.

## Fitur MVP

- Tanpa login.
- Upload PDF maksimal 10 MB.
- Ekstraksi teks PDF dengan `pypdf`.
- Generator soal AI via Gemini API dengan fallback lokal opsional.
- Quiz pilihan ganda.
- Halaman hasil dan pembahasan.
- Penyimpanan session quiz dengan SQLite.

## Cara Menjalankan Lokal

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

## Konfigurasi Gemini

Buat file `.env` di root project, lalu simpan API key Gemini sebagai environment variable server-side:

```env
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.0-flash
GEMINI_FALLBACK_ENABLED=true
GEMINI_MAX_INPUT_CHARS=9000
PDF_MAX_PAGES=24
```

API key tidak boleh dikirim ke frontend. Aplikasi Flask ini memanggil Gemini dari backend, jadi user publik bisa memakai website tanpa melihat API key.

## Proteksi PDF Besar

Aplikasi tidak mengirim semua isi PDF besar ke AI. Backend mengambil maksimal `PDF_MAX_PAGES` halaman yang tersebar, membersihkan teks, lalu membatasi input Gemini dengan `GEMINI_MAX_INPUT_CHARS`. Jika Gemini gagal atau output JSON-nya rusak, `GEMINI_FALLBACK_ENABLED=true` membuat aplikasi tetap mencoba generator lokal.

## Catatan

PDF harus berisi teks yang bisa diseleksi. PDF hasil scan gambar belum didukung karena belum memakai OCR.
