import csv
import pandas as pd
from re import fullmatch
from functools import wraps
from sqlalchemy import text
from zoneinfo import ZoneInfo
from datetime import timedelta
from io import StringIO, BytesIO
from flask import Blueprint, request, render_template, redirect, url_for, session, Response

from .models.user import User
from .models.record import Record
from .models.admins import Admin
from .extensions import db

bp = Blueprint("main", __name__)

MILESTONE = 15
TAIPEI = ZoneInfo("Asia/Taipei")

# ---------------- Helpers ----------------
def get_current_user():
    account = session.get("account")
    if not account:
        return None
    return User.query.get(account)

def is_admin(user: User) -> bool:
    return Admin.query.get(user.account) is not None

def is_valid_password(password: str) -> bool:
    return bool(fullmatch(r"[a-zA-Z0-9-_]+", password))

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not get_current_user():
            return redirect(url_for("main.login_get"))
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        u = get_current_user()
        if not u:
            return redirect(url_for("main.login_get"))
        if not is_admin(u):
            return redirect(url_for("main.index"))
        return f(*args, **kwargs)
    return wrapper

# ---------------- Routes ----------------
@bp.get("/")
def index():
    user = get_current_user()
    if user:
        records = (
            Record.query.filter_by(user_account=user.account)
            .order_by(Record.time.desc())
            .all()
        )
        is_admin = Admin.query.get(user.account) is not None
        return render_template(
            "index.html",
            user=user,
            is_admin=is_admin,
            records=records,
            milestone=MILESTONE,
        )
    return render_template("index.html", user=None, milestone=MILESTONE)

# --- Auth ---
@bp.get("/login")
def login_get():
    if get_current_user():
        return redirect(url_for("main.index"))
    return render_template("login.html")

@bp.post("/login")
def login_post():
    account = request.form.get("account","").strip()
    password = request.form.get("password","")
    remember = request.form.get("remember", "session")

    if not account.isdigit() or not (len(account) == 9):
        return render_template("login.html", error="帳號需為 9 位數字。"), 400
    if len(password) < 4 or len(password) > 20:
        return render_template("login.html", error="密碼需為 4 到 20 碼。"), 400

    user = User.query.get(account)
    if not user or not user.check_password(password):
        return render_template("login.html", error="帳號或密碼錯誤。"), 401

    session["account"] = account
    
    if remember == "session":
        session.permanent = False
    elif remember == "7days":
        session.permanent = True
        bp.permanent_session_lifetime = timedelta(days=7)
    elif remember == "forever":
        session.permanent = True
        bp.permanent_session_lifetime = timedelta(days=365*10)
    
    return redirect(url_for("main.index"))

@bp.get("/logout")
def logout():
    session.pop("account", None)
    return redirect(url_for("main.index"))

# --- Registration ---
@bp.get("/register")
def register_get():
    if get_current_user():
        return redirect(url_for("main.index"))
    return render_template("register.html")

@bp.post("/register")
def register_post():
    account = request.form.get("account","").strip()
    name = request.form.get("name","").strip()
    password = request.form.get("password","")
    confirm = request.form.get("confirm","")

    if not account.isdigit() or not (len(account) == 9):
        return render_template("register.html", error="帳號需為 9 位數字。"), 400
    if not name or len(name) < 2:
        return render_template("register.html", error="姓名至少需 2 個字。"), 400
    if len(password) < 4 or len(password) > 20:
        return render_template("register.html", error="密碼長度需為 4 到 20 碼內。"), 400
    if not is_valid_password(password):
        return render_template("register.html", error="密碼只能包含數字、英文字母、 '-' 和 '_' 。"), 400
    if password != confirm:
        return render_template("register.html", error="兩次密碼不一致。"), 400
    if User.query.get(account):
        return render_template("register.html", error="此帳號已存在。"), 400

    user = User(account=account, name=name)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    SUPER_ADMIN = "113062206"   # your account
    if not Admin.query.get(SUPER_ADMIN):
        db.session.add(Admin(account=SUPER_ADMIN))
        db.session.commit()

    return redirect(url_for("main.login_get"))

# --- Admin dashboard ---
@bp.get("/admin")
@admin_required
def admin():
    user = get_current_user()
    target_account = request.args.get("target", "").strip()
    target = None
    records = None
    is_admin = False
    
    

    # All users overview
    all_users = []
    for u in User.query.all():
        pts = sum(r.amount for r in u.records)
        all_users.append({
            "account": u.account,
            "name": u.name,
            "points": pts,
            "count": len(u.records),
        })

    if target_account:
        target_user = User.query.get(target_account)
        if target_user:
            records = (
                Record.query.filter_by(user_account=target_account)
                .order_by(Record.time.desc())
                .all()
            )
            is_admin = Admin.query.get(target_user.account) is not None
            points = sum(r.amount for r in records)
            target = {"account": target_user.account,
                      "name": target_user.name,
                      "points": points}
        else:
            return render_template(
                "admin.html",
                user=user,
                target=None,
                records=None,
                all_users=all_users,
                milestone=MILESTONE,
                error="找不到該帳號。",
            )

    return render_template(
        "admin.html",
        user=user,
        target=target,
        is_admin=is_admin,
        records=records,
        all_users=all_users,
        milestone=MILESTONE,
    )

@bp.post("/admin/adjust")
@admin_required
def admin_adjust():
    account = request.form.get("account", "").strip()
    op = request.form.get("op", "add")
    amount_raw = request.form.get("amount", "0").strip()
    reason = request.form.get("reason", "").strip()

    target = User.query.get(account)
    if not target:
        return redirect(url_for("main.admin", target=account))

    try:
        amt = int(amount_raw)
    except ValueError:
        return redirect(url_for("main.admin", target=account))

    if amt == 0:
        return redirect(url_for("main.admin", target=account))
    if not reason:
        return redirect(url_for("main.admin", target=account))

    # Normalize sign
    if op == "add" and amt < 0: amt = abs(amt)
    if op == "remove" and amt > 0: amt = -amt

    rec = Record(user=target,
                 type="add" if amt > 0 else "remove",
                 amount=amt,
                 reason=reason)
    
    target.points += amt
    db.session.add(rec)
    db.session.commit()

    return redirect(url_for("main.admin", target=account))

@bp.post("/admin/record/update")
@admin_required
def admin_record_update():
    account = request.form.get("account", "").strip()
    rec_id_raw = request.form.get("id", "").strip()   # pass record.id instead of idx
    typ = request.form.get("type", "").strip()        # 'add' or 'remove'
    amount_raw = request.form.get("amount", "").strip()
    reason = request.form.get("reason", "").strip()

    # --- Validation ---
    target = User.query.get(account)
    if not target:
        return redirect(url_for("main.admin", target=account))

    try:
        rec_id = int(rec_id_raw)
    except ValueError:
        return redirect(url_for("main.admin", target=account))

    try:
        amt = int(amount_raw)
    except ValueError:
        return redirect(url_for("main.admin", target=account))

    if typ not in ("add", "remove"):
        return redirect(url_for("main.admin", target=account))
    if not reason:
        return redirect(url_for("main.admin", target=account))

    # Normalize sign
    if typ == "add" and amt < 0:
        amt = abs(amt)
    if typ == "remove" and amt > 0:
        amt = -amt

    # --- Update the record ---
    rec = Record.query.filter_by(id=rec_id, user_account=account).first()
    if not rec:
        return redirect(url_for("main.admin", target=account))

    # Adjust user points: remove old, apply new
    target.points -= rec.amount
    target.points += amt

    rec.type = "add" if amt > 0 else "remove"
    rec.amount = amt
    rec.reason = reason
    # keep original time
    db.session.commit()

    return redirect(url_for("main.admin", target=account))


@bp.post("/admin/record/delete")
@admin_required
def admin_record_delete():
    account = request.form.get("account", "").strip()
    rec_id_raw = request.form.get("id", "").strip()

    target = User.query.get(account)
    if not target:
        return redirect(url_for("main.admin"))
    
    try:
        rec_id = int(rec_id_raw)
    except ValueError:
        return redirect(url_for("main.admin", target=account))

    rec = Record.query.filter_by(id=rec_id, user_account=account).first()
    if not rec:
        return redirect(url_for("main.admin", target=account))

    # Adjust points before deleting
    target.points -= rec.amount

    db.session.delete(rec)
    db.session.commit()

    return redirect(url_for("main.admin", target=account))

@bp.post("/admin/toggle_admin")
@admin_required
def toggle_admin():
    account = request.form.get("account", "").strip()
    user = User.query.get(account)
    if not user:
        return redirect(url_for("main.admin"))
    if user.account == "113062206":
        return redirect(url_for("main.admin"))

    existing = Admin.query.get(account)
    if existing:
        # remove admin entry
        db.session.delete(existing)
    else:
        # add admin entry
        db.session.add(Admin(account=account))

    db.session.commit()
    return redirect(url_for("main.admin", target=account))

@bp.get("/admins")
@admin_required
def admins_list():
    # join Admin + User for details
    admins = (
        db.session.query(Admin, User)
        .join(User, Admin.account == User.account)
        .all()
    )
    return render_template("adminlist.html", admins=admins, milestone=MILESTONE, user=get_current_user())

@bp.route("/export", methods=["GET", "POST"])
def export():
    tables = ["Users", "Records", "Admins"]
    
    if request.method == "POST":
        table = request.form["table"]
        format_ = request.form["format"]
        
        query = ""
        if table == "Users":
            query = "SELECT account, name, password_hash, points FROM users"
        elif table == "Records":
            query = f"""
                SELECT id, user_account, (time AT TIME ZONE 'Asia/Taipei') AS time,
                    type, amount, reason
                FROM records
            """
        elif table == "Admins":
            query = "SELECT account FROM admins"
            
        rows = db.session.execute(text(query)).mappings().all()

        if not rows:
            return "No data in table."

        columns = rows[0].keys()
        
        # Export as CSV
        if format_ == "csv":
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")

            writer.writeheader()
            writer.writerows(rows)
            
            csv_text = "\ufeff" + output.getvalue()

            return Response(
                csv_text,
                mimetype="text/csv",
                headers={"Content-Disposition": f"attachment;filename={table}.csv"},
            )

        # Export as Excel
        elif format_ == "excel":
            df = pd.DataFrame(rows, columns=columns)
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name=table)
            output.seek(0)
            return Response(
                output,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment;filename={table}.xlsx"},
            )

        # Export as SQL (INSERT statements)
        elif format_ == "sql":
            sql_lines = []

            # Quote column names for Postgres
            colnames = ", ".join([f'"{col}"' for col in columns])
            placeholders = ", ".join([f":{col}" for col in columns])

            stmt = text(f"INSERT INTO {table} ({colnames}) VALUES ({placeholders});")

            for row in rows:
                # Compile statement with bound parameters
                compiled = stmt.bindparams(**row).compile(
                    dialect=db.engine.dialect,
                    compile_kwargs={"literal_binds": True}
                )
                sql_lines.append(str(compiled))

            sql_text = "\n".join(sql_lines)
            return Response(
                sql_text,
                mimetype="text/sql",
                headers={"Content-Disposition": f"attachment;filename={table}.sql"},
            )

    return render_template("export.html", tables=tables)
