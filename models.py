from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy import func

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    name = db.Column(db.String(150), nullable=False)  # Add the name field
    # email = db.Column(db.String(120), unique=True, nullable=False)

    favorite_dishes = db.relationship('FavoriteDish', backref='user', cascade='all, delete-orphan')
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    # other fields...

    # Establish relationship with FavoriteDish with cascade delete
    favorite_dishes = db.relationship('FavoriteDish', backref='user', cascade='all, delete-orphan')

class SearchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    search_term = db.Column(db.String(150), nullable=False)

class FavoriteDish(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    dish_name = db.Column(db.String(150), nullable=False)
