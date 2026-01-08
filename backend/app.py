import os
import json
import whisper
from datetime import datetime
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    session,
)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret")

# Load Whisper model (Small is a good balance of speed and accuracy)
# Ensure you have 'ffmpeg' installed on your system for this to work.
model = whisper.load_model("small")

# Simple JSON file to persist patient records for this prototype
PATIENTS_FILE = os.path.join(os.path.dirname(__file__), "patients.json")


def load_patients():
    if not os.path.exists(PATIENTS_FILE):
        return []
    with open(PATIENTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_patients(patients):
    with open(PATIENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(patients, f, indent=2, ensure_ascii=False)


def find_patient(pid):
    patients = load_patients()
    for p in patients:
        if str(p.get("id")) == str(pid):
            return p
    return None


def require_nurse(func):
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("nurse_logged_in"):
            return redirect(url_for("nurse_login", next=request.path))
        return func(*args, **kwargs)

    return wrapper


@app.route("/")
def index():
    """Renders a public landing page with link to login."""
    return render_template("index.html")


@app.route("/nurse/login", methods=["GET", "POST"])
def nurse_login():
    """Simple nurse login for this prototype. Replace with real auth in production."""
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        # WARNING: hardcoded credential for prototype only
        if username == "nurse" and password == "password":
            session["nurse_logged_in"] = True
            return redirect(request.args.get("next") or url_for("patient_list"))
        error = "Invalid credentials"
    return render_template("login.html", error=error)


@app.route("/nurse/logout")
def nurse_logout():
    session.pop("nurse_logged_in", None)
    return redirect(url_for("index"))


@app.route("/patients")
@require_nurse
def patient_list():
    patients = load_patients()
    return render_template("patient_list.html", patients=patients)


@app.route("/patients/new", methods=["GET", "POST"])
@require_nurse
def patient_new():
    if request.method == "POST":
        data = request.form.to_dict()
        patients = load_patients()
        new_id = max([p.get("id", 0) for p in patients] or [0]) + 1
        patient = {
            "id": new_id,
            "name": data.get("name", ""),
            "address": data.get("address", ""),
            "age": data.get("age", ""),
            "height": data.get("height", ""),
            "weight": data.get("weight", ""),
            "previous_visit": data.get("previous_visit", ""),
            "medical_history": data.get("medical_history", ""),
            "prescription": data.get("prescription", ""),
            "transcripts": [],
        }
        patients.append(patient)
        save_patients(patients)
        return redirect(url_for("patient_list"))
    return render_template("patient_profile.html", patient=None)


@app.route("/patients/<int:pid>")
@require_nurse
def patient_view(pid):
    patient = find_patient(pid)
    if not patient:
        return "Patient not found", 404
    return render_template("patient_profile.html", patient=patient)


@app.route("/patients/<int:pid>/edit", methods=["GET", "POST"])
@require_nurse
def patient_edit(pid):
    patients = load_patients()
    patient = find_patient(pid)
    if not patient:
        return "Patient not found", 404
    if request.method == "POST":
        data = request.form.to_dict()
        # update fields
        for key in ["name", "address", "age", "height", "weight", "previous_visit", "medical_history", "prescription"]:
            patient[key] = data.get(key, patient.get(key, ""))
        save_patients(patients)
        return redirect(url_for("patient_view", pid=pid))
    return render_template("patient_profile.html", patient=patient, edit=True)


@app.route("/patients/<int:pid>/transcribe")
@require_nurse
def patient_transcribe_page(pid):
    patient = find_patient(pid)
    if not patient:
        return "Patient not found", 404
    return render_template("transcription.html", patient=patient)


@app.route("/transcribe", methods=["POST"])
def transcribe():
    """Handles audio upload, conversion, transcription, and optional patient association."""

    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio"]
    input_path = "input.webm"
    output_path = "final.wav"

    patient_id = request.form.get("patient_id") or request.args.get("patient_id")

    try:
        # 1. Save the recorded audio from the client
        audio_file.save(input_path)

        # 2. Convert WebM (browser default) to WAV (Whisper preferred) using FFmpeg
        os.system(f'ffmpeg -y -i "{input_path}" "{output_path}"')

        # 3. Transcribe audio using the Whisper model
        result = model.transcribe(output_path, language="en")
        text = result.get("text", "").strip()
        text = text.replace("<|en|>", "").replace("<|ja|>", "")

        # 4. If patient_id provided, append transcript to their history
        if patient_id:
            patients = load_patients()
            for p in patients:
                if str(p.get("id")) == str(patient_id):
                    p.setdefault("transcripts", []).append({
                        "text": text,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    })
                    save_patients(patients)
                    break

        return jsonify({"text": text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        # 5. Clean up temporary files regardless of success or failure
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)


if __name__ == "__main__":
    app.run(debug=True)