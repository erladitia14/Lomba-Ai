import json
import uuid
from datetime import datetime

from .extensions import db


class QuizSession(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = db.Column(db.String(255), nullable=False)
    questions_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    results = db.relationship("QuizResult", backref="session", lazy=True)

    @property
    def questions(self):
        return json.loads(self.questions_json)

    @questions.setter
    def questions(self, value):
        self.questions_json = json.dumps(value, ensure_ascii=False)


class QuizResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey("quiz_session.id"), nullable=False)
    user_answers_json = db.Column(db.Text, nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def user_answers(self):
        return json.loads(self.user_answers_json)

    @user_answers.setter
    def user_answers(self, value):
        self.user_answers_json = json.dumps(value, ensure_ascii=False)
