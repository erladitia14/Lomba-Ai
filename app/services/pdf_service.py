from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader
from werkzeug.utils import secure_filename


@dataclass(frozen=True)
class PdfExtractionResult:
    text: str
    page_count: int
    pages_read: int
    truncated: bool


def allowed_file(filename, allowed_extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


def get_safe_filename(file_storage):
    return secure_filename(file_storage.filename)


def extract_text_from_pdf(file_storage, max_pages=None, max_chars=None):
    return extract_text_with_metadata(file_storage, max_pages=max_pages, max_chars=max_chars).text


def extract_text_with_metadata(file_storage, max_pages=None, max_chars=None):
    file_storage.stream.seek(0)
    pdf_bytes = BytesIO(file_storage.read())
    reader = PdfReader(pdf_bytes)

    if reader.is_encrypted:
        try:
            decrypt_result = reader.decrypt("")
        except Exception as exc:
            raise ValueError("PDF terenkripsi dan tidak bisa dibaca otomatis.") from exc
        if not decrypt_result:
            raise ValueError("PDF terenkripsi dan tidak bisa dibaca otomatis.")

    page_count = len(reader.pages)
    page_indices = _select_page_indices(page_count, max_pages)
    pages = []
    total_chars = 0
    truncated = bool(max_pages and page_count > max_pages)
    pages_read = 0

    for page_index in page_indices:
        pages_read += 1
        text = (reader.pages[page_index].extract_text() or "").strip()
        if not text:
            continue

        if max_chars and total_chars + len(text) > max_chars:
            remaining = max_chars - total_chars
            if remaining > 0:
                pages.append(text[:remaining])
            truncated = True
            break

        pages.append(text)
        total_chars += len(text)

    return PdfExtractionResult(
        text="\n".join(pages).strip(),
        page_count=page_count,
        pages_read=pages_read,
        truncated=truncated,
    )


def _select_page_indices(page_count, max_pages):
    if page_count <= 0:
        return []
    if not max_pages or max_pages >= page_count:
        return list(range(page_count))
    if max_pages <= 1:
        return [0]

    step = (page_count - 1) / (max_pages - 1)
    return sorted({round(index * step) for index in range(max_pages)})
