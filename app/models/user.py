from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from ..extensions import db

class User(db.Model):
    __tablename__ = "users"
    
    account = db.Column(db.String(9), primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    points = db.Column(db.Integer, default=0, nullable=False)
    
    records = db.relationship(
        "Record",
        foreign_keys="Record.user_account",
        back_populates="user", 
        cascade="all, delete-orphan"
    )
    authored_records = db.relationship(
        "Record",
        foreign_keys="Record.author_account",
        back_populates="author"
    )
    logs = db.relationship(
        "Log", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.account} points={self.points}>"