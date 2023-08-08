from datetime import datetime
import secrets
from flask import Flask, flash, render_template, redirect, request, session, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    current_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate


app = Flask(__name__)

db = SQLAlchemy()
migrate = Migrate(app, db)

# Change this to a random secret key
app.config["SECRET_KEY"] = secrets.token_hex(16)

# Replace with your database URL
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///bank.db"

login_manager = LoginManager(app)
login_manager.login_view = "login"
db.init_app(app)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    balance = db.Column(db.Float, default=0)

    @classmethod
    def find_by_username(cls, username):
        return cls.query.filter_by(username=username).first()


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(10), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("transactions", lazy=True))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            login_user(user)
            flash("Login successful", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password", "error")
    return render_template("login.html")


# LOGOUT
@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("login"))


# REGISTER
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        hashed_password = generate_password_hash(password)
        new_user = User(username=user, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("register.html")


# DASHBOARD
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", user=current_user)


@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():
    if request.method == "POST":
        amount = float(request.form.get("amount"))
        if amount > 0:
            new_deposit = Transaction(
                user_id=current_user.id, amount=amount, transaction_type="deposit"
            )
            db.session.add(new_deposit)
            current_user.balance += amount
            db.session.commit()
            flash(f"Deposit of ${amount:.2f} successful!", "success")
        else:
            flash("Invalid deposit amount!", "error")
    return render_template("dashboard.html", user=current_user)


@app.route("/withdraw", methods=["GET", "POST"])
@login_required
def withdraw():
    if request.method == "POST":
        amount = float(request.form.get("amount"))
        if 0 < amount <= current_user.balance:
            new_withdrawal = Transaction(
                user_id=current_user.id, amount=amount, transaction_type="withdrawal"
            )
            db.session.add(new_withdrawal)
            current_user.balance -= amount
            db.session.commit()
            flash(f"Withdrawal of ${amount:.2f} successful!", "success")
        else:
            flash("Invalid withdrawal amount!", "error")
    return render_template("dashboard.html", user=current_user)


@app.route("/transfer", methods=["GET", "POST"])
@login_required
def transfer():
    current_user = User.query.get(session["user_id"])

    if request.method == "POST":
        recipient_username = request.form.get("recipient_username")
        amount = float(request.form.get("amount"))

        recipient = User.query.filter_by(username=recipient_username).first()

        if (
            recipient
            and recipient != current_user
            and amount > 0
            and amount <= current_user.balance
        ):
            current_user.balance -= amount
            recipient.balance += amount

            # Record sender's transaction
            sender_transaction = Transaction(
                user=current_user,
                amount=-amount,
                transaction_type="Transfer to " + recipient_username,
            )
            db.session.add(sender_transaction)

            # Record recipient's transaction
            recipient_transaction = Transaction(
                user=recipient,
                amount=amount,
                transaction_type="Transfer from " + current_user.username,
            )
            db.session.add(recipient_transaction)
            db.session.commit()
            flash(
                f"Transfer of ${amount:.2f} to {recipient_username} successful!",
                "success",
            )
        else:
            flash("Invalid transfer details!", "error")
    return render_template("dashboard.html", user=current_user)


if __name__ == "__main__":
    app.run(debug=True)
