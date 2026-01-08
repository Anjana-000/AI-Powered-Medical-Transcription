let recorder;
let audioChunks = [];
let timer;
let seconds = 0;

const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");
const status = document.getElementById("status");
const output = document.getElementById("output");

// DEBUG (keep this for now)
console.log("JS loaded", startBtn, stopBtn);

startBtn.addEventListener("click", async () => {
    try {
        audioChunks = [];
        seconds = 0;
        output.innerText = "";

        status.innerText = "Recording...";

        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        recorder = new MediaRecorder(stream);

        recorder.ondataavailable = e => {
            if (e.data.size > 0) {
                audioChunks.push(e.data);
            }
        };

        recorder.start();

        timer = setInterval(() => {
            seconds++;
            status.innerText = `Recording... ${seconds}s`;
        }, 1000);

        startBtn.disabled = true;
        stopBtn.disabled = false;

    } catch (err) {
        alert("Microphone error: " + err.message);
        console.error(err);
    }
});

stopBtn.addEventListener("click", () => {
    recorder.stop();
    clearInterval(timer);

    status.innerText = "Transcribing...";

    recorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
        const formData = new FormData();
        formData.append("audio", audioBlob);
        // If a global PATIENT_ID is set by template, include it
        if (typeof PATIENT_ID !== "undefined" && PATIENT_ID) {
            formData.append("patient_id", String(PATIENT_ID));
        }

        const response = await fetch("/transcribe", {
            method: "POST",
            body: formData
        });

        const data = await response.json();
        output.innerText = data.text;

        status.innerText = "Transcription complete";

        startBtn.disabled = false;
        stopBtn.disabled = true;
    };
});
