from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from werkzeug.exceptions import RequestEntityTooLarge

from .extensions import db
from .models import QuizResult, QuizSession
from .services.pdf_service import allowed_file, extract_text_with_metadata, get_safe_filename
from .services.question_generator import generate_questions
from .services.text_cleaner import clean_text

main_bp = Blueprint("main", __name__)


def register_error_handlers(app):
    app.register_error_handler(RequestEntityTooLarge, handle_large_file)


def _upload_context():
    max_upload_mb = current_app.config.get("MAX_CONTENT_LENGTH", 0) // (1024 * 1024)
    return {
        "max_upload_mb": max(1, max_upload_mb),
        "pdf_max_pages": current_app.config.get("PDF_MAX_PAGES") or "beberapa",
    }


@main_bp.route("/")
def index():
    return render_template("index.html")


def handle_large_file(_exc):
    max_mb = _upload_context()["max_upload_mb"]
    flash(f"Ukuran PDF terlalu besar. Batas upload saat ini {max_mb} MB.", "error")
    return redirect(url_for("main.upload"))


@main_bp.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "GET":
        return render_template("upload.html", **_upload_context())

    file = request.files.get("pdf_file")
    try:
        total_questions = int(request.form.get("total_questions", 10))
    except ValueError:
        total_questions = 10
    total_questions = max(1, min(total_questions, 15))

    if not file or file.filename == "":
        flash("Pilih file PDF terlebih dahulu.", "error")
        return redirect(url_for("main.upload"))

    if not allowed_file(file.filename, current_app.config["ALLOWED_EXTENSIONS"]):
        flash("File harus berformat PDF.", "error")
        return redirect(url_for("main.upload"))

    try:
        filename = get_safe_filename(file)
        extraction = extract_text_with_metadata(
            file,
            max_pages=current_app.config.get("PDF_MAX_PAGES"),
            max_chars=current_app.config.get("PDF_MAX_TEXT_CHARS"),
        )
        cleaned_text = clean_text(
            extraction.text,
            max_chars=current_app.config.get("CLEAN_TEXT_MAX_CHARS"),
        )

        was_truncated = extraction.truncated

        if len(cleaned_text) < 200:
            flash("Teks PDF terlalu sedikit atau PDF tidak bisa dibaca. Gunakan PDF yang berisi teks, bukan scan gambar.", "error")
            return redirect(url_for("main.upload"))

        questions = generate_questions(cleaned_text, total_questions)

        if not questions:
            flash("Soal belum bisa dibuat dari PDF ini. Coba gunakan materi dengan paragraf yang lebih panjang.", "error")
            return redirect(url_for("main.upload"))

        quiz_session = QuizSession(filename=filename)
        quiz_session.questions = questions
        db.session.add(quiz_session)
        db.session.commit()

        if was_truncated:
            flash(
                f"PDF besar terdeteksi ({extraction.page_count} halaman). "
                f"Sistem mengambil {extraction.pages_read} halaman yang tersebar agar token AI tidak cepat habis.",
                "info",
            )

        return redirect(url_for("main.quiz", session_id=quiz_session.id))
    except Exception as exc:
        current_app.logger.exception(exc)
        flash(f"Terjadi kesalahan saat memproses PDF atau membuat soal dengan AI: {exc}", "error")
        return redirect(url_for("main.upload"))


@main_bp.route("/quiz/<session_id>", methods=["GET", "POST"])
def quiz(session_id):
    quiz_session = QuizSession.query.get_or_404(session_id)
    questions = quiz_session.questions

    if request.method == "GET":
        return render_template("quiz.html", quiz_session=quiz_session, questions=questions)

    user_answers = {}
    correct = 0

    for index, question in enumerate(questions):
        selected = request.form.get(f"question_{index}")
        user_answers[str(index)] = selected
        if selected == question["answer"]:
            correct += 1

    score = round((correct / len(questions)) * 100)
    result = QuizResult(
        session_id=quiz_session.id,
        score=score,
        total_questions=len(questions),
    )
    result.user_answers = user_answers
    db.session.add(result)
    db.session.commit()

    return redirect(url_for("main.result", result_id=result.id))


@main_bp.route("/result/<int:result_id>")
def result(result_id):
    quiz_result = QuizResult.query.get_or_404(result_id)
    questions = quiz_result.session.questions
    user_answers = quiz_result.user_answers
    correct_count = sum(
        1
        for index, question in enumerate(questions)
        if user_answers.get(str(index)) == question["answer"]
    )
    return render_template(
        "result.html",
        quiz_result=quiz_result,
        questions=questions,
        correct_count=correct_count,
    )
