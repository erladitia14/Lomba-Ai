from io import BytesIO

from pypdf import PdfReader
from werkzeug.utils import secure_filename


def allowed_file(filename, allowed_extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


def get_safe_filename(file_storage):
    
    return secure_filename(file_storage.filename)


def extract_text_from_pdf(file_storage):
    file_storage.stream.seek(0)
    pdf_bytes = BytesIO(file_storage.read())
    reader = PdfReader(pdf_bytes)
    pages = []

    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text)

    return "\n".join(pages).strip()
