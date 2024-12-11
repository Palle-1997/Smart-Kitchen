import pandas as pd
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

app = Flask(__name__, template_folder='../frontend/templates')  # Specify the template folder
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Load dataset
df = pd.read_csv('/workspaces/Smart-Kitchen/smart_kitchen_assistant/backend/data/Food_Recipe.csv')

# Function to find recipes based on ingredients
def find_recipes(user_ingredients):
    user_ingredients = set([ingredient.strip().lower() for ingredient in user_ingredients.split(',')])  # Clean user input
    matching_recipes = []

    # Loop through the dataset and find matching recipes
    for index, row in df.iterrows():
        # Ensure 'ingredients_name' is a valid string
        if isinstance(row['ingredients_name'], str):
            recipe_ingredients = set([ingredient.strip().lower() for ingredient in row['ingredients_name'].split(',')])
        else:
            recipe_ingredients = set()

        # Check if there’s an overlap between the user's ingredients and the recipe's ingredients
        if user_ingredients.intersection(recipe_ingredients):
            matching_recipes.append({
                'name': row['name'],
                'description': row['description'],
                'ingredients': row['ingredients_name'],
                'instructions': row['instructions']
            })
   #sort the receips to 
    top_5_recipes = sorted(matching_recipes, key=lambda x: len(set(x['ingredients'].split(',')).intersection(user_ingredients)), reverse=True)[:5]
    return top_5_recipes

# Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)

class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.String(50))

class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipe = db.Column(db.String(200), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and bcrypt.check_password_hash(user.password, request.form['password']):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid credentials.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', username=current_user.username)

@app.route('/inventory', methods=['GET', 'POST'])
@login_required
def inventory():
    if request.method == 'POST':
        item = request.form['item']
        quantity = request.form['quantity']
        inventory_item = Inventory(user_id=current_user.id, item=item, quantity=quantity)
        db.session.add(inventory_item)
        db.session.commit()
        flash('Item added to inventory!', 'success')
    user_inventory = Inventory.query.filter_by(user_id=current_user.id).all()
    return render_template('inventory.html', inventory=user_inventory)

@app.route('/inventory/update/<int:id>', methods=['GET', 'POST'])
@login_required
def update_inventory(id):
    inventory_item = Inventory.query.get_or_404(id)
    if inventory_item.user_id != current_user.id:
        flash('You are not authorized to update this item.', 'danger')
        return redirect(url_for('inventory'))

    if request.method == 'POST':
        inventory_item.item = request.form['item']
        inventory_item.quantity = request.form['quantity']
        db.session.commit()
        flash('Inventory item updated successfully!', 'success')
        return redirect(url_for('inventory'))

    return render_template('update_inventory.html', inventory_item=inventory_item)

@app.route('/inventory/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def delete_inventory(id):
    inventory_item = Inventory.query.get_or_404(id)
    if inventory_item.user_id != current_user.id:
        flash('You are not authorized to delete this item.', 'danger')
        return redirect(url_for('inventory'))

    db.session.delete(inventory_item)
    db.session.commit()
    flash('Inventory item deleted successfully!', 'success')
    return redirect(url_for('inventory'))


@app.route('/favorites', methods=['GET', 'POST'])
@login_required
def favorites():
    if request.method == 'POST':
        recipe = request.form['recipe']
        favorite = Favorite(user_id=current_user.id, recipe=recipe)
        db.session.add(favorite)
        db.session.commit()
        flash('Recipe added to favorites!', 'success')
    user_favorites = Favorite.query.filter_by(user_id=current_user.id).all()
    return render_template('favorites.html', favorites=user_favorites)

@app.route('/favorites/update/<int:id>', methods=['GET', 'POST'])
@login_required
def update_favorite(id):
    favorite_recipe = Favorite.query.get_or_404(id)
    if favorite_recipe.user_id != current_user.id:
        flash('You are not authorized to update this recipe.', 'danger')
        return redirect(url_for('favorites'))

    if request.method == 'POST':
        favorite_recipe.recipe = request.form['recipe']
        db.session.commit()
        flash('Favorite recipe updated successfully!', 'success')
        return redirect(url_for('favorites'))

    return render_template('update_favorite.html', favorite_recipe=favorite_recipe)

@app.route('/favorites/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def delete_favorite(id):
    favorite_recipe = Favorite.query.get_or_404(id)
    if favorite_recipe.user_id != current_user.id:
        flash('You are not authorized to delete this recipe.', 'danger')
        return redirect(url_for('favorites'))

    db.session.delete(favorite_recipe)
    db.session.commit()
    flash('Favorite recipe deleted successfully!', 'success')
    return redirect(url_for('favorites'))

@app.route('/recommend-recipes', methods=['GET', 'POST'])
@login_required
def recommend_recipes_route():
    recommendations = []
    ingredients = []

    if request.method == 'POST':
        ingredients = request.form['ingredients']  # Get ingredients from user input
        recommendations = find_recipes(ingredients)  # Find matching recipes

        if recommendations:
            flash('Recipes found!', 'success')
        else:
            flash('No recipes found for the given ingredients.', 'warning')

    return render_template('recipe_recommendation.html', recommendations=recommendations, ingredients=ingredients)

# Initialize the database tables
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Manually create tables
    app.run(debug=True, port=5001)


