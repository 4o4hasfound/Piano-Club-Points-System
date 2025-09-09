from sqlalchemy.sql import func
from ..extensions import db

class Log(db.Model):
    __tablename__ = "logs"

    id = db.Column(db.Integer, primary_key=True)
    user_account = db.Column(db.String(9), db.ForeignKey("users.account", ondelete="CASCADE"), nullable=False)

    time = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    url = db.Column(db.Text, nullable=False)
    log = db.Column(db.Text)

    user = db.relationship(
        "User", 
        foreign_keys=[user_account], 
        back_populates="logs",
        passive_deletes=True
    )

    def __repr__(self):
        return f"<Log {self.user_account} : {self.log}>"