import csv
import os
import pandas as pd
from re import fullmatch
from functools import wraps
from sqlalchemy import text, func, or_, select
from zoneinfo import ZoneInfo
from datetime import timedelta
from io import StringIO, BytesIO
from math import ceil
from flask import Blueprint, request, render_template, redirect, url_for, session, Response, send_from_directory, current_app

from .models.user import User
from .models.record import Record
from .models.admin import Admin
from .models.log import Log
from .extensions import db

bp = Blueprint("main", __name__)

MILESTONE = 15
TAIPEI = ZoneInfo("Asia/Taipei")
MIN_POINT_UPDATE = -100
MAX_POINT_UPDATE = 100

def clamp_amount_update(amount: int) -> int:
    return min(max(amount, MIN_POINT_UPDATE), MAX_POINT_UPDATE)

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
        
    rec = Log(user=user,
              url="/register")
    db.session.add(rec)
    db.session.commit()
        
    return redirect(url_for("main.login_get"))

# --- Admin dashboard ---
@bp.get("/admin")
@admin_required
def admin():
    user = get_current_user()
    target_account = request.args.get("target", "").strip()
    targets_str = target_account
    target_accounts = targets_str.split(',') if target_account else None
    
    search = request.args.get("search", "").strip()
    sort = request.args.get("sort", "account_asc")
    page = request.args.get("page", 1, type=int)
    per_page = 20

    target = None
    targets = None
    records = None
    is_admin = False
    
    query = (
        select(
            User.account,
            User.name,
            func.coalesce(func.sum(Record.amount), 0).label("points"),
            func.count(Record.id).label("count"),
        )
        .outerjoin(Record, User.account == Record.user_account)
        .group_by(User.account, User.name)
    )
    
    if search:
        query = query.filter(
            or_(
                User.account.ilike(f"%{search}%"),
                User.name.ilike(f"%{search}%"),
            )
        )
        
    if sort == "account_asc":
        query = query.order_by(User.account.asc())
    elif sort == "account_desc":
        query = query.order_by(User.account.desc())
    elif sort == "name_asc":
        query = query.order_by(User.name.asc())
    elif sort == "name_desc":
        query = query.order_by(User.name.desc())
    elif sort == "points_asc":
        query = query.order_by(func.coalesce(func.sum(Record.amount), 0).asc())
    elif sort == "points_desc":
        query = query.order_by(func.coalesce(func.sum(Record.amount), 0).desc())
        
    count_query = select(func.count()).select_from(query.subquery())
    total = db.session.execute(count_query).scalar()
    total_pages = ceil(total / per_page)
    
    statement = query.order_by(User.account).limit(per_page).offset((page - 1) * per_page)    
    all_users = db.session.execute(statement).all()
    
    if target_accounts and len(target_accounts) > 1:
        targets_user = User.query.filter(User.account.in_(target_accounts)).all()
        
        if targets_user:
            targets = [{
                "account": t.account,
                "name": t.name,
                "points": sum(r.amount for r in t.records),
            } for t in targets_user]
        else:
            return render_template(
                "admin.html",
                user=user,
                target=None,
                targets=None,
                is_admin=is_admin,
                records=None,
                page=page,
                all_users=[],
                total_pages=0,
                page_indexes=[],
                search=search,
                sort=sort,
                milestone=MILESTONE,
                error="找不到批次帳號。",
            )
    elif target_account:
        target_user = User.query.get(target_account)
        if target_user:
            records = target_user.records
            is_admin = Admin.query.get(target_user.account) is not None
            points = sum(r.amount for r in records)
            target = {
                "account": target_user.account,
                "name": target_user.name,
                "points": points,
            }
        else:
            return render_template(
                "admin.html",
                user=user,
                target=None,
                targets=None,
                is_admin=is_admin,
                records=None,
                page=page,
                all_users=[],
                total_pages=0,
                page_indexes=[],
                search=search,
                sort=sort,
                milestone=MILESTONE,
                error="找不到該帳號。",
            )
    
    page_indexes = list(range(
        max(1, page - 2), 
        min(total_pages, page + 2) + 1
    ))
    
    return render_template(
        "admin.html",
        user=user,
        target=target,
        targets=targets,
        targets_str=targets_str,
        is_admin=is_admin,
        records=records,
        page=page,
        all_users=all_users,
        total_pages=total_pages,
        page_indexes=page_indexes,
        search=search,
        sort=sort,
        milestone=MILESTONE,
    )

@bp.post("/admin/adjust")
@admin_required
def admin_adjust():
    account = request.form.get("account", "").strip()
    op = request.form.get("op", "add")
    amount_raw = request.form.get("amount", "0").strip()
    reason = request.form.get("reason", "").strip()
    user = get_current_user()

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
    
    amt = clamp_amount_update(amt)

    if user:
        rec = Record(user=target,
                    author=user,
                    type="add" if amt > 0 else "remove",
                    amount=amt,
                    reason=reason)
        
        target.points += amt
        db.session.add(rec)
        db.session.commit()
        
        log = Log(user=user,
                url="/admin/adjust",
                log=f"{'Add' if amt > 0 else 'Remove'} {abs(amt)} points {'from' if amt > 0 else 'to'} {target.account} {target.name} for the reason [ {reason} ]")
        db.session.add(log)
        db.session.commit()

    return redirect(url_for("main.admin", target=account))


@bp.post("/admin/batch_adjust")
@admin_required
def admin_batch_adjust():
    accounts_str = request.form.get("accounts", "").strip()
    accounts = accounts_str.split(',')
    op = request.form.get("op", "add")
    amount_raw = request.form.get("amount", "0").strip()
    reason = request.form.get("reason", "").strip()
    user = get_current_user()
    
    accounts = list(set(accounts))

    for account in accounts:
        target = User.query.get(account)
        if not target:
            continue

        try:
            amt = int(amount_raw)
        except ValueError:
            continue

        if amt == 0:
            continue
        if not reason:
            continue

        # Normalize sign
        if op == "add" and amt < 0: amt = abs(amt)
        if op == "remove" and amt > 0: amt = -amt
        
        amt = clamp_amount_update(amt)

        if user:
            rec = Record(user=target,
                        author=user,
                        type="add" if amt > 0 else "remove",
                        amount=amt,
                        reason=reason)
            
            target.points += amt
            db.session.add(rec)
            db.session.commit()
            
            log = Log(user=user,
                    url="/admin/batch_adjust",
                    log=f"{'Add' if amt > 0 else 'Remove'} {abs(amt)} points {'from' if amt > 0 else 'to'} {target.account} {target.name} for the reason [ {reason} ]")
            db.session.add(log)
            db.session.commit()

    return redirect(url_for("main.admin", target=accounts_str))

@bp.post("/admin/record/update")
@admin_required
def admin_record_update():
    account = request.form.get("account", "").strip()
    rec_id_raw = request.form.get("id", "").strip()   # pass record.id instead of idx
    typ = request.form.get("type", "").strip()        # 'add' or 'remove'
    amount_raw = request.form.get("amount", "").strip()
    reason = request.form.get("reason", "").strip()
    user = get_current_user()

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
        
    amt = clamp_amount_update(amt)

    # --- Update the record ---
    rec = Record.query.filter_by(id=rec_id, user_account=account).first()
    if not rec:
        return redirect(url_for("main.admin", target=account))
    
    rec_old_amount = rec.amount
    rec_old_reason = rec.reason

    # Adjust user points: remove old, apply new
    target.points -= rec.amount
    target.points += amt

    rec.type = "add" if amt > 0 else "remove"
    rec.amount = amt
    rec.reason = reason
    # keep original time
    db.session.commit()
    
    if user:
        log_message = f"Updated record {rec.id} for {account} ( "
        if rec.amount == rec_old_amount and rec.reason == rec_old_reason:
            log_message += "NO changes "
        if rec.amount != rec_old_amount:
            log_message += f"amount: {rec_old_amount} -> {rec.amount} ; "
        if rec.reason != rec_old_reason:
            log_message += f"reason: {rec_old_reason} -> {rec.reason} ; "
        log_message += ")"
        log = Log(user=user,
                url="/admin/record/update",
                log=log_message)
        db.session.add(log)
        db.session.commit()

    return redirect(url_for("main.admin", target=account))


@bp.post("/admin/record/delete")
@admin_required
def admin_record_delete():
    account = request.form.get("account", "").strip()
    rec_id_raw = request.form.get("id", "").strip()
    user = get_current_user()

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

    if user:
        tw_time = rec.time.astimezone(ZoneInfo("Asia/Taipei"))
        formatted = tw_time.strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"Delete record {rec.id} for {account} with ( time = {formatted} ; type = {rec.type} ; amount = {rec.amount} ; reason = {rec.reason} )"
        log = Log(user=user,
                url="/admin/record/update",
                log=log_message)
        db.session.add(log)
        db.session.commit()
        
    db.session.delete(rec)
    db.session.commit()
    
    return redirect(url_for("main.admin", target=account))

@bp.get("/admin/batch_user_remove")
@admin_required
def admin_batch_user_remove():
    accounts_str = request.args.get("accounts", "").strip()
    accounts = accounts_str.split(',')
    target_account = request.args.get("target", "").strip()
    accounts.remove(target_account)

    return redirect(url_for("main.admin", target=",".join(accounts)))

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
        action = "removed from"
    else:
        # add admin entry
        db.session.add(Admin(account=account))
        action = "granted"

    db.session.commit()
    
    log = Log(user=user,
            url="/admin/record/update",
            log=f"{account} was {action} admin")
    db.session.add(log)
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
    
        user = get_current_user()
        if user:
            log = Log(user=user,
                    url="/export",
                    log=f"Export {table} as {format_}")
            db.session.add(log)
            db.session.commit()

    return render_template("export.html", tables=tables)

@bp.route("/logs")
def logs():
    q = request.args.get("q", "")
    page = request.args.get("page", 1, type=int)
    per_page = 20

    query = Log.query.order_by(Log.time.desc())
    if q:
        query = query.filter(Log.log.ilike(f"%{q}%"))
        
    count_query = select(func.count()).select_from(query.subquery())
    total = db.session.execute(count_query).scalar()
    total_pages = ceil(total / per_page)
    
    query = query.limit(per_page).offset((page - 1) * per_page)
    logs = query.all()
    
    page_indexes = list(range(
        max(1, page - 2), 
        min(total_pages, page + 2) + 1
    ))
    
    return render_template(
        "logs.html",
        logs=logs,
        total_pages=total_pages,
        page=page,
        page_indexes=page_indexes,
        q=q
    )
    
@bp.route('/favicon.ico')
def favicon():
    return send_from_directory(
        'static', 
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )