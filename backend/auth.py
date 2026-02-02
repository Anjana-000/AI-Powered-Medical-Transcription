from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, login_required
from werkzeug.security import check_password_hash
from bson import ObjectId
from models import Doctor

auth = Blueprint('auth', __name__)

def init_auth(login_manager):
    @login_manager.user_loader
    def load_user(user_id):
        return Doctor.get(current_app.mongo, user_id)
@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        
        mongo = current_app.mongo
        if Doctor.find_by_username(mongo, username):
            flash('Username already exists')
        else:
            from werkzeug.security import generate_password_hash
            hashed = generate_password_hash(password)
            Doctor.create_user(mongo, username, hashed, email)
            flash('Registration successful! Please login.')
            return redirect(url_for('auth.login'))
            
    return render_template('register.html')

@auth.route('/login', methods=['GET', 'POST']) # <--- THIS WAS MISSING
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        mongo = current_app.mongo
        doctor = Doctor.find_by_username(mongo, username)
        
        if doctor:
            # Re-fetch the raw document to get the hashed password
            raw_user = mongo.db.doctors.find_one({"_id": ObjectId(doctor.id)})
            if raw_user and check_password_hash(raw_user['password'], password):
                login_user(doctor)
                return redirect(url_for('patient_list'))
            else:
                flash('Invalid username or password')
        else:
            flash('Invalid username or password')
                
    return render_template('login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))
