from sqlalchemy import CheckConstraint
from sqlalchemy.sql import func
from ..extensions import db

class Record(db.Model):
    __tablename__ = "records"

    id = db.Column(db.Integer, primary_key=True)
    user_account = db.Column(db.String(9), db.ForeignKey("users.account", ondelete="CASCADE"), nullable=False)
    author_account = db.Column(db.String(9), db.ForeignKey("users.account"), nullable=False)

    time = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # type: "add" or "remove"
    type = db.Column(db.String(7), nullable=False)

    amount = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(255), nullable=True)

    user = db.relationship(
        "User",
        z=[user_account],
        back_populates="records",
        passive_deletes=True
    )

    author = db.relationship(
        "User",
        foreign_keys=[author_account],
        back_populates="authored_records"
    )
    
    __table_args__ = (
        CheckConstraint("amount != 0"),
        CheckConstraint("type IN ('add','remove')"),
    )

    def __repr__(self):
        return f"<Record {self.type} {self.amount} for {self.user_account}>"