from flask import Flask, render_template, request, redirect, url_for, flash
import os
import numpy as np
import google.generativeai as genai
from tensorflow.keras.preprocessing import image
from tensorflow.keras.models import load_model
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask import make_response
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, current_user, logout_user
from flask import render_template
from models import User, SearchHistory, FavoriteDish
from sqlalchemy import func


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///recipe_gen.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
migrate = Migrate(app, db)

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel('gemini-pro')

# Load your trained model
keras_model = load_model('v1_inceptionV3.keras')

# Class mapping for predictions
class_mapping = {
    0: 'Burger', 1: 'Butter Naan', 2: 'Chai', 3: 'Chapati', 4: 'Chole Bhature',
    5: 'Dal Makhani', 6: 'Dhokla', 7: 'Fried Rice', 8: 'Idli', 9: 'Jalebi',
    10: 'Kaathi Rolls', 11: 'Kadai Paneer', 12: 'Kulfi', 13: 'Masala Dosa',
    14: 'Momos', 15: 'Paani Puri', 16: 'Pakode', 17: 'Pav Bhaji', 18: 'Pizza',
    19: 'Samosa'
}

def predict_food(img_path):
    img_width, img_height = 299, 299
    img = image.load_img(img_path, target_size=(img_height, img_width))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    img_array /= 255.0

    prediction = keras_model.predict(img_array)
    predicted_class_index = np.argmax(prediction)
    predicted_class_label = class_mapping[predicted_class_index]

    return predicted_class_label

def get_gemini_response(food_item):
    try:
        prompt = f"Generate ingredients and a recipe for {food_item}."
        response = gemini_model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating recipe: {e}"

# User Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)

# Search History Model
class SearchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    search_term = db.Column(db.String(150), nullable=False)

# Favorite Dishes Model
class FavoriteDish(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dish_name = db.Column(db.String(100), nullable=False)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='favorite_dishes')


# Admin View for Users
class UserModelView(ModelView):
    # Only allow admin users to access the admin panel
    def is_accessible(self):
        return current_user.is_authenticated and current_user.username == 'admin'

    # Columns to display
    column_list = ['id', 'username']

# Initialize Flask-Admin
admin = Admin(app, name='Admin Panel', template_mode='bootstrap3')
admin.add_view(UserModelView(User, db.session))


@app.route('/admin_page')
# @login_required  # Ensure only logged-in users can access
def admin_page():
    return render_template('admin_page.html')

@app.route('/admin_dashboard')
# @login_required  # Ensure only logged-in users can access
def admin_dashboard():
    return render_template('admin_dashboard.html')  # Create this template as needed

@app.route('/manage_users')
# @login_required  # Ensure only admin can access this route
def manage_users():
    users = User.query.all()  # Fetch all users from the database
    return render_template('manage_users.html', users=users)

@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash(f'Username {username} is already taken. Please choose a different username.')
            return redirect(url_for('add_user'))

        # Create a new user and add to the database
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()  # Commit the transaction to save the user in the database

        flash(f'User {username} has been added successfully!')
        return redirect(url_for('manage_users'))

    return render_template('add_user.html')  # Render the add user form

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
# @login_required  # Ensure only admin can access this route
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.username = request.form['username']
        # You may want to handle password changes here too
        db.session.commit()
        flash('User updated successfully!', 'success')
        return redirect(url_for('manage_users'))
    
    return render_template('edit_user.html', user=user)

@app.route('/delete_user/<int:user_id>', methods=['POST'])
# @login_required  
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    try:
        # Delete user along with associated favorite dishes
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'danger')

    return redirect(url_for('manage_users'))


@app.route('/view_recipes')
def view_recipes():
    # Query all favorites along with related user info
    favorites = FavoriteDish.query.join(User).all()

    # Pass the favorites list to the template
    return render_template('view_recipes.html', favorites=favorites)


@app.route('/site_statistics')
def site_statistics():
    # Total Users
    total_users = User.query.count()

    # Total Search Queries
    total_searches = SearchHistory.query.count()

    # Total Favorite Dishes
    total_favorites = FavoriteDish.query.count()

    # Top 5 most popular search terms
    top_searches = db.session.query(
    SearchHistory.search_term, func.count(SearchHistory.search_term).label('count')).group_by(SearchHistory.search_term).order_by(db.desc('count')).limit(5).all()
  
    # Top 5 most favorited dishes
    top_favorite_dishes = db.session.query(
    FavoriteDish.dish_name, func.count(FavoriteDish.dish_name).label('count')).group_by(FavoriteDish.dish_name).order_by(db.desc('count')).limit(5).all()
    # Pass all statistics to the template
    return render_template('site_statistics.html', 
                           total_users=total_users,
                           total_searches=total_searches,
                           total_favorites=total_favorites,
                           top_searches=top_searches,
                           top_favorite_dishes=top_favorite_dishes)
# User Loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
def landing_page():
    return render_template('landing_page.html')

@app.route('/favorites')
@login_required
def favorites():
    # Assuming you have a FavoriteDish model and current_user is authenticated
    favorite_dishes = FavoriteDish.query.filter_by(user_id=current_user.id).all()
    return render_template('favorites.html', favorite_dishes=favorite_dishes)

@app.route('/remove_favorite/<int:dish_id>', methods=['POST'])
@login_required
def remove_favorite(dish_id):
    dish = FavoriteDish.query.get_or_404(dish_id)
    
    if dish.user_id != current_user.id:
        flash("You don't have permission to remove this favorite.", "danger")
        return redirect(url_for('favorites'))

    db.session.delete(dish)
    db.session.commit()
    flash(f'{dish.dish_name} removed from your favorites.', 'success')
    return redirect(url_for('favorites'))

@app.route('/add_to_favorites', methods=['POST'])
@login_required
def add_to_favorites():
    dish_name = request.form.get('dish_name')
    if dish_name:
        # Check if the dish is already a favorite for the user
        existing_favorite = FavoriteDish.query.filter_by(user_id=current_user.id, dish_name=dish_name).first()
        if not existing_favorite:
            # Add the dish to the favorites if not already added
            new_favorite = FavoriteDish(user_id=current_user.id, dish_name=dish_name)
            db.session.add(new_favorite)
            db.session.commit()
            flash('Recipe added to your favorites!', 'success')
        else:
            flash('Recipe is already in your favorites.', 'info')
    else:
        flash('No recipe to add.', 'danger')
    
    return redirect(url_for('get_started'))

@app.route('/home')
@login_required
def home():
    response = make_response(render_template('home.html', current_user=current_user))
    response.headers['Cache-Control'] = 'no-store'
    return response

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Query the database for the user
        user = User.query.filter_by(username=username).first()

        if user and user.password == password:  # Direct password comparison
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/faq')
def faqs():
    return render_template('faqs.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/get_started', methods=['GET', 'POST'])
@login_required
def get_started():
    if request.method == 'POST':
        if 'image' not in request.files:
            return redirect(request.url)
        
        file = request.files['image']
        if file.filename == '':
            return redirect(request.url)

        if file:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(image_path)

            predicted_food = predict_food(image_path)
            recipe = get_gemini_response(predicted_food)

            return render_template('get_started.html', prediction=predicted_food, image_path=image_path, recipe=recipe)

    return render_template('get_started.html')

if __name__ == '__main__':
    app.run(debug=True)
