from flask import Flask, render_template
from datetime import datetime, timezone
from datetime import timedelta
from sqlalchemy import inspect

from .models.log import Log
from .extensions import db, migrate
from . import routes

def cleanup_logs():
    inspector = inspect(db.engine)
    if "logs" not in inspector.get_table_names():
        return

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    db.session.query(Log).filter(Log.time < cutoff).delete()
    db.session.commit()
        
def create_app(config_class="app.config.Config"):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    
    # init extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # register routes
    app.register_blueprint(routes.bp)
    
    with app.app_context():
        cleanup_logs()
    
    return app