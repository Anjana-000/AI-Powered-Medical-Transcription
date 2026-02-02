import os
import whisper
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, current_app, send_from_directory
from flask_pymongo import PyMongo
from flask_login import LoginManager, login_required, current_user
from werkzeug.security import generate_password_hash
from bson.objectid import ObjectId

from auth import auth, init_auth
from models import Doctor, Patient

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret")

# MongoDB Config
app.config["MONGO_URI"] = "mongodb://localhost:27017/cms_db"
app.mongo = PyMongo(app)

# Flask-Login Config
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

# Initialize User Loader
init_auth(login_manager)

# Register Blueprint
app.register_blueprint(auth)

# Upload Config
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Load Whisper (kept from original)
model = whisper.load_model("small")

# CLI Command to create initial doctor
@app.cli.command("create-doctor")
def create_doctor():
    """Creates a default doctor user."""
    username = input("Username: ")
    email = input("Email: ")
    password = input("Password: ")
    hashed = generate_password_hash(password)
    
    if Doctor.find_by_username(app.mongo, username):
        print("User already exists.")
        return

    Doctor.create_user(app.mongo, username, hashed, email)
    print(f"Doctor {username} created successfully.")

@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for('patient_list'))
    return redirect(url_for('auth.login'))

@app.route("/dashboard")
@login_required
def patient_list():
    query = request.args.get('search', '')
    if query:
        patients = Patient.search(app.mongo, query)
    else:
        patients = Patient.get_all(app.mongo)
    return render_template("dashboard.html", patients=patients, search_query=query)

@app.route("/patients/new", methods=["GET", "POST"])
@login_required
def patient_new():
    if request.method == "POST":
        data = request.form.to_dict()
        Patient.create(app.mongo, data)
        return redirect(url_for("patient_list"))
    return render_template("add_patient.html")

@app.route("/patients/<pid>")
@login_required
def patient_view(pid):
    patient = Patient.get_by_id(app.mongo, pid)
    if not patient:
        return "Patient not found", 404
    return render_template("patient_profile.html", patient=patient)

@app.route("/patients/<pid>/consultation", methods=["POST"])
@login_required
def add_consultation(pid):
    text = request.form.get("notes")
    if text:
        Patient.add_consultation(app.mongo, pid, {
            "text": text,
            "date": datetime.utcnow().isoformat(),
            "doctor": current_user.username
        })
    return redirect(url_for("patient_view", pid=pid))

@app.route("/patients/<pid>/upload", methods=["POST"])
@login_required
def upload_file_route(pid):
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    if file:
        filename = f"{pid}_{int(datetime.now().timestamp())}_{file.filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        Patient.add_file(app.mongo, pid, {
            "filename": filename,
            "original_name": file.filename,
            "url": url_for('static', filename=f'uploads/{filename}')
        })
        
    return redirect(url_for("patient_view", pid=pid))

@app.route("/transscribe", methods=["POST"])
def transcribe():
    # Keep transcription logic but adapt for MongoDB
    # For now, just simplistic adaptation or keep as is but point to new Patient logic
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio"]
    input_path = "input.webm"
    output_path = "final.wav"
    patient_id = request.form.get("patient_id")

    try:
        audio_file.save(input_path)
        os.system(f'ffmpeg -y -i "{input_path}" "{output_path}"')
        result = model.transcribe(output_path, language="en")
        text = result.get("text", "").strip()

        if patient_id:
            # Assuming patient_id is ObjectId str
            Patient.add_consultation(app.mongo, patient_id, {
                "text": text,
                "date": datetime.utcnow().isoformat(),
                "type": "transcription"
            })

        return jsonify({"text": text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(output_path): os.remove(output_path)

if __name__ == "__main__":
    app.run(debug=True)