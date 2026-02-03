import whisper

model = whisper.load_model("base")

audio_path = "backend/audio/sample.wav"

print("Whisper model loaded successfully.")
print("Waiting for audio file at:", audio_path)
import whisper
import subprocess
import os

# Load model once
model = whisper.load_model("small")

def transcribe_audio(audio_path):
    wav_path = audio_path.replace(".webm", ".wav")

    # Convert to WAV
    subprocess.run(
        ["ffmpeg", "-y", "-i", audio_path, wav_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # Transcription
    result = model.transcribe(wav_path, language="en")

    # Cleanup
    if os.path.exists(audio_path):
        os.remove(audio_path)
    if os.path.exists(wav_path):
        os.remove(wav_path)

    return result["text"]
