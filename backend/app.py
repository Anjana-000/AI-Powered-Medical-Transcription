import os
import whisper
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, current_app, send_from_directory
from flask_pymongo import PyMongo
from flask_login import LoginManager, login_required, current_user
from werkzeug.security import generate_password_hash
from bson.objectid import ObjectId

from auth import auth, init_auth
from models import Doctor, Patient
import os
from flask import Flask

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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

# Custom Template Filter for Time
@app.template_filter('format_time')
def format_time(value):
    try:
        if not value: return ""
        dt = datetime.fromisoformat(value)
        return dt.strftime("%I:%M %p")
    except ValueError:
        return value

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

@app.route("/patients/<pid>", methods=["GET", "PUT"])
@login_required
def patient_view(pid):
    if request.method == "PUT":
        data = request.json
        Patient.update(app.mongo, pid, data)
        return jsonify({"success": True})

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
            "id": uuid.uuid4().hex,
            "text": text,
            "date": datetime.now().isoformat(),
            "doctor": current_user.username
        })
    return redirect(url_for("patient_view", pid=pid, tab='consultation'))

@app.route("/patients/<pid>/consultation/<cid>/delete", methods=["POST"])
@login_required
def delete_consultation(pid, cid):
    Patient.delete_consultation(app.mongo, pid, cid)
    return redirect(url_for("patient_view", pid=pid, tab='consultation'))

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
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio"]
    if audio_file.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    unique_id = uuid.uuid4().hex
    input_filename = f"temp_input_{unique_id}_{audio_file.filename}"
    output_filename = f"temp_output_{unique_id}.wav"
    
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], input_filename)
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)

    try:
        audio_file.save(input_path)
        
        if not os.path.exists(input_path) or os.path.getsize(input_path) < 100:
             print(f"DEBUG: Saved file is too small: {os.path.getsize(input_path)} bytes")
             return jsonify({"error": "File save failed or empty file. Size < 100 bytes"}), 400

        # Use subprocess to capture ffmpeg output and ensure it runs
        import subprocess
        command = [
            'ffmpeg', '-y', 
            '-i', input_path, 
            '-ar', '16000', 
            '-ac', '1', 
            '-c:a', 'pcm_s16le', 
            output_path
        ]
        
        print(f"DEBUG: Running ffmpeg: {' '.join(command)}")
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            print("DEBUG: ffmpeg stdout:", result.stdout)
            print("DEBUG: ffmpeg stderr:", result.stderr)
        except subprocess.CalledProcessError as e:
            print("ERROR: ffmpeg failed")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)
            return jsonify({"error": f"Audio processing failed: {e.stderr}"}), 500
        except FileNotFoundError:
            return jsonify({"error": "ffmpeg not found on server. Please install ffmpeg."}), 500

        if not os.path.exists(output_path) or os.path.getsize(output_path) < 100:
             print(f"DEBUG: Output WAV too small: {os.path.getsize(output_path) if os.path.exists(output_path) else 'Missing'}")
             return jsonify({"error": "Converted audio file is empty or corrupted"}), 500

        print(f"DEBUG: Transcription starting for {output_path}")
        result = model.transcribe(output_path, language="en", fp16=False) # Disable fp16 for CPU safety
        text = result.get("text", "").strip()
        print(f"DEBUG: Transcription result: {text[:50]}...")

        return jsonify({"text": text})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Server Error: {str(e)}"}), 500
    finally:
        # Cleanup
        if os.path.exists(input_path):
            try: os.remove(input_path)
            except: pass
        if os.path.exists(output_path):
            try: os.remove(output_path)
            except: pass

if __name__ == "__main__":
    app.run(debug=True)