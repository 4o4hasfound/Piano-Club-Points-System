from datetime import datetime
from sqlalchemy import CheckConstraint
from ..extensions import db

class Record(db.Model):
    __tablename__ = "records"

    id = db.Column(db.Integer, primary_key=True)
    user_account = db.Column(db.String(9), db.ForeignKey("users.account"), nullable=False)

    time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # type: "add" or "remove"
    type = db.Column(db.String(7), nullable=False)

    amount = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(255), nullable=True)

    # backref to user
    user = db.relationship("User", back_populates="records")
    
    __table_args__ = (
        CheckConstraint("amount != 0"),
        CheckConstraint("type IN ('add','remove')"),
    )

    def __repr__(self):
        return f"<Record {self.type} {self.amount} for {self.user_account}>"