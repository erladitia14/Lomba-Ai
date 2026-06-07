import os
from werkzeug.utils import secure_filename
from pypdf import PdfReader


def allowed_file(filename, allowed_extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


def save_pdf(file_storage, upload_folder):
    os.makedirs(upload_folder, exist_ok=True)
    filename = secure_filename(file_storage.filename)
    path = os.path.join(upload_folder, filename)
    file_storage.save(path)
    return filename, path


def extract_text_from_pdf(path):
    reader = PdfReader(path)
    pages = []

    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text)

    return "\n".join(pages).strip()
