from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from .extensions import db
from .models import QuizResult, QuizSession
from .services.pdf_service import allowed_file, extract_text_from_pdf, save_pdf
from .services.question_generator import generate_questions
from .services.text_cleaner import clean_text

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "GET":
        return render_template("upload.html")

    file = request.files.get("pdf_file")
    total_questions = int(request.form.get("total_questions", 10))

    if not file or file.filename == "":
        flash("Pilih file PDF terlebih dahulu.", "error")
        return redirect(url_for("main.upload"))

    if not allowed_file(file.filename, current_app.config["ALLOWED_EXTENSIONS"]):
        flash("File harus berformat PDF.", "error")
        return redirect(url_for("main.upload"))

    try:
        filename, path = save_pdf(file, current_app.config["UPLOAD_FOLDER"])
        raw_text = extract_text_from_pdf(path)
        cleaned_text = clean_text(raw_text)

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

        return redirect(url_for("main.quiz", session_id=quiz_session.id))
    except Exception as exc:
        current_app.logger.exception(exc)
        flash("Terjadi kesalahan saat memproses PDF. Coba file lain.", "error")
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
    return render_template("result.html", quiz_result=quiz_result, questions=questions)
