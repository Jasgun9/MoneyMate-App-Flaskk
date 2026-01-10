from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
import os
from datetime import datetime
import json
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "info"

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    # optional relationships (nice to have)
    expenses = db.relationship("Expense", backref="user", lazy=True)
    goals = db.relationship("Goals", backref="user", lazy=True)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

class Expense(db.Model):
    Eid = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    isExpense = db.Column(db.Boolean, nullable=False, default=True)
    # typee = db.Column(db.String(120), nullable=False)  # payment method
    amount = db.Column(db.Float, nullable=False)
    dateAdded = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    category = db.Column(db.String(80), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)


class Goals(db.Model):
    Gid = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)   # target
    Saving = db.Column(db.Float, nullable=False)   # saved so far
    dateAdded = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# @app.before_first_request
# def create_tables():
#     db.create_all()

_tables_created = False

@app.before_request
def create_tables_once():
    global _tables_created
    if not _tables_created:
        db.create_all()
        _tables_created = True

# ======================
# HELPERS
# ======================


with open("config.json") as f:
    SITE_CONFIG = json.load(f)


def expense_to_dict(e: Expense):
    return {
        "id": e.Eid,
        "title": e.title,
        "category": e.category,
        # "method": e.typee,
        "amount": e.amount,
        "isExpense": e.isExpense,
        "date": e.dateAdded.isoformat(),
        "date_display": e.dateAdded.strftime("%d %b"),
    }


def goal_to_dict(g: Goals):
    return {
        "id": g.Gid,
        "title": g.title,
        "target": g.amount,
        "saved": g.Saving,
        "progress": 0 if g.amount == 0 else round((g.Saving / g.amount) * 100, 1),
        "date": g.dateAdded.isoformat(),
    }


# ======================
# PAGE ROUTES
# ======================

@app.route("/")
@login_required

def index():
    # totals
    income = (
        db.session.query(func.coalesce(func.sum(Expense.amount), 0.0))
        .filter(Expense.user_id == current_user.id, Expense.isExpense == False)
        .scalar()
    )
    expense = (
        db.session.query(func.coalesce(func.sum(Expense.amount), 0.0))
        .filter(Expense.user_id == current_user.id, Expense.isExpense == True)
        .scalar()
    )
    goalmoney = (
        db.session.query(func.coalesce(func.sum(Goals.Saving), 0.0)).filter(Goals.user_id == current_user.id).scalar()
        )
    balance = (income - expense) - goalmoney

    # latest 5 expenses
    latest_expenses = (
        Expense.query.filter_by(user_id=current_user.id).
        order_by(Expense.dateAdded.desc(), Expense.Eid.desc())
        .limit(5)
        .all()
    )

    # a few goals
    goals = Goals.query.filter_by(user_id=current_user.id).order_by(Goals.dateAdded.desc()).limit(3).all()
    allexpenses = (
        Expense.query
        .filter_by(user_id=current_user.id)
        .order_by(Expense.dateAdded.desc())
        .all()
    )
    return render_template(
        "index.html",
        balance=balance,
        income=income,
        expense=expense,
        latest_expenses=latest_expenses,
        goals=goals,
        allexpenses=allexpenses
    )




@app.context_processor
def inject_config():
    return dict(config=SITE_CONFIG)

@app.route("/updategoalsaving", methods=["POST"])
@login_required
def update_goal_saving():
    data = request.get_json() or {}

    goal_id = data.get("id")
    # print(data.get("id"))
    new_saved = data.get("saved")

    try:
        goal_id = int(goal_id)
        new_saved = float(new_saved)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Invalid data"}), 400

    # goal = Goals.query.filter_by(Gid=goal_id, user_id=current_user.id).first()
    goal = Goals.query.filter(Goals.Gid == goal_id, Goals.user_id == current_user.id).first()
    if not goal:
        return jsonify({"ok": False, "error": "Goal not found"}), 404

    if new_saved < 0:
        new_saved = 0

    goal.Saving = new_saved
    db.session.commit()

    return jsonify({"ok": True})





@app.route("/deleteGoal", methods=["POST"])
@login_required
def delete_goal():
    data = request.get_json()
    goal_id = data.get("goal_id")

    goal = Goals.query.filter_by(user_id=current_user.id, Gid=goal_id).first()
    if not goal:
        return jsonify(success=False), 404

    db.session.delete(goal)
    db.session.commit()

    return jsonify(success=True)







@app.route("/transactions", methods=["GET", "POST"])
@login_required

def transactions_page():
    expenses = (
        Expense.query.filter_by(user_id=current_user.id).order_by(Expense.dateAdded.desc(), Expense.Eid.desc())
        .all()
    )
    if request.method == "POST":
        return jsonify([expense_to_dict(e) for e in expenses])
    return render_template("transactions.html", expenses=expenses)


@app.route("/goals", methods=["GET", "POST"])
@login_required

def goals_page():
    goals = Goals.query.filter_by(user_id=current_user.id).order_by(Goals.dateAdded.desc(), Goals.Gid.desc()).all()
    if request.method == "POST":
        return jsonify([goal_to_dict(g) for g in goals])
    return render_template("goals.html", goals=goals)

    

# ======================
# JSON API ROUTES (AJAX)
# ======================

@app.route("/add_transaction")
@login_required

def add_transaction():
    title = request.args.get("title")
    isExpense = request.args.get("isExpense")
    # typee = request.args.get("typee")
    amount = request.args.get("amount")
    dateAdded = request.args.get("dateAdded")
    category = request.args.get("category")
    if dateAdded:
        try:
            date_obj = datetime.fromisoformat(dateAdded).date()
        except ValueError:
            date_obj = datetime.utcnow().date()
    else:
        date_obj = datetime.utcnow().date()
    exp = Expense(
        title=title,
        isExpense=bool(int(isExpense)),
        # typee=typee,
        amount=float(amount),
        dateAdded=date_obj,
        category=category,
        user_id=current_user.id
    )
    print(exp)
    db.session.add(exp)
    db.session.commit()
    return "Success"



@app.route("/add_goals")
@login_required

def add_goals():
    title = request.args.get("title")
    amount = request.args.get("amount")
    saving = request.args.get("saving")
    dateAdded = request.args.get("dateAdded")
    if dateAdded:
        try:
            date_obj = datetime.fromisoformat(dateAdded).date()
        except ValueError:
            date_obj = datetime.utcnow().date()
    else:
        date_obj = datetime.utcnow().date()
    goal = Goals(
        title=title,
        amount=float(amount),
        Saving=float(saving),
        dateAdded=date_obj,
        user_id=current_user.id
    )
    db.session.add(goal)
    db.session.commit()
    return "Success"








@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            # redirect to next page if exists, else dashboard
            next_page = request.args.get("next")
            return redirect(next_page or url_for("index"))
        else:
            flash("Invalid email or password", "error")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm") or ""

        if not email or not password:
            flash("Email and password are required", "error")
        elif password != confirm:
            flash("Passwords do not match", "error")
        else:
            existing = User.query.filter_by(email=email).first()
            if existing:
                flash("Email already registered, please login.", "error")
            else:
                user = User(email=email)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                flash("Account created! You can now log in.", "success")
                return redirect(url_for("login"))

    return render_template("signup.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))





if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
