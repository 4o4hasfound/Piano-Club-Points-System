from flask import Flask, render_template
import html

from .models import user
from .extensions import db, migrate
from . import routes

def create_app(config_class="app.config.Config"):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    
    # init extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # register routes
    app.register_blueprint(routes.bp)
    
    @app.before_request
    def ensure_super_admin():
        from app.models.admins import Admin
        from app.extensions import db
        SUPER_ADMIN = "113062206"   # your account
        if not Admin.query.get(SUPER_ADMIN):
            db.session.add(Admin(account=SUPER_ADMIN))
            db.session.commit()
            
    # @app.error_handler_spec(400)
    # @app.error_handler_spec(404)
    # def bad_request(e):
    #     reason = getattr(e, "description", "Bad request")
    #     safe_reason = html.escape(str(reason))
    #     return render_template("error.html", code=e.code, reason=safe_reason)
    
    
    # @app.errorhandler(500)
    # def server_error(e):
    #     db.session.rollback()
    #     reason = getattr(e, "description", "Bad request")
    #     safe_reason = html.escape(str(reason))
    #     return render_template("error.html", code=e.code, reason=safe_reason)

    return app