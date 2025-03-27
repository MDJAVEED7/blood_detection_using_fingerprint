from flask import Flask, request, render_template, jsonify, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
import tensorflow as tf
from PIL import Image
import numpy as np
import os
import gdown
from werkzeug.security import generate_password_hash, check_password_hash

# ----> Install dependencies: pip install -r requirements.txt <----

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ✅ User Model (Now uses password hashing)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # Hashed password

# ✅ Google Drive Model Download
FILE_ID = "1-4pICY0ssOYUP4adgfC6-mD4rdzF4MLH"  # Replace with your actual file ID
MODEL_PATH = "vggbest_model.keras"
MODEL_URL = f"https://drive.google.com/uc?id={FILE_ID}"

if not os.path.exists(MODEL_PATH):
    print("📥 Downloading model from Google Drive...")
    gdown.download(MODEL_URL, MODEL_PATH, quiet=False)

# ✅ Load the trained model
print("🔄 Loading model...")
model = tf.keras.models.load_model(MODEL_PATH)
print("✅ Model loaded successfully!")

# ✅ Preprocess Image Function
def preprocess_image(image):
    if image.mode != 'RGB':
        image = image.convert('RGB')

    img = image.resize((224, 224))
    img_array = np.array(img) / 255.0  # Normalize
    img_array = np.expand_dims(img_array, axis=0)  # Add batch dimension
    return img_array

# ✅ Routes
@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash('⚠ Username already exists. Choose a different one.')
            return redirect(url_for('signup'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('✅ Signup successful. Please log in.')
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):  # Secure check
            session['user_id'] = user.id
            flash('✅ Login successful')
            return redirect(url_for('prediction'))
        else:
            flash('⚠ Invalid credentials')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('✅ Logged out successfully')
    return redirect(url_for('landing'))

@app.route('/prediction', methods=['GET', 'POST'])
def prediction():
    if 'user_id' not in session:
        flash('⚠ Please log in to access this page')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    username = user.username

    prediction = None
    if request.method == 'POST':
        file = request.files['file']
        if not file:
            flash('⚠ No file uploaded!')
            return redirect(url_for('prediction'))

        try:
            img = Image.open(file)
            processed_img = preprocess_image(img)

            result = model.predict(processed_img)
            predicted_class = np.argmax(result)
            classes = ['A+', 'A-', 'AB+', 'AB-', 'B+', 'B-', 'O+', 'O-']
            prediction = classes[predicted_class]

            return jsonify({'prediction': prediction})
        except Exception as e:
            flash(f'⚠ Error processing image: {str(e)}')
            return redirect(url_for('prediction'))

    return render_template('prediction.html', prediction=prediction, username=username)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
