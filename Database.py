from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    isExpense = db.Column(db.Boolean, nullable=False, default=True)
    type = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    dateAdded = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    category = db.Column(db.String(80), nullable=True)

class Goals(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    Saving = db.Column(db.Float, nullable=False)
    dateAdded = db.Column(db.Date, nullable=False, default=datetime.utcnow)


