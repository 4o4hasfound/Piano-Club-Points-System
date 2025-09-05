from ..extensions import db

class Admin(db.Model):
    __tablename__ = "admins"

    account = db.Column(db.String(9), db.ForeignKey("users.account"), primary_key=True)

    # relationship back to User (optional)
    user = db.relationship("User", backref="admin_entry")