
let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let timerInterval;
let seconds = 0;

// Elements
const recordBtn = document.getElementById("recordBtn");
const status = document.getElementById("status");
const output = document.getElementById("output");
const timer = document.getElementById("timer");
const editBtn = document.getElementById("editBtn");
const saveBtn = document.getElementById("saveBtn");

/* ================= TIMER FUNCTIONS ================= */

function startTimer() {
    seconds = 0;
    timer.innerText = "00:00";

    timerInterval = setInterval(() => {
        seconds++;
        const min = String(Math.floor(seconds / 60)).padStart(2, "0");
        const sec = String(seconds % 60).padStart(2, "0");
        timer.innerText = `${min}:${sec}`;
    }, 1000);
}

function stopTimer() {
    clearInterval(timerInterval);
}

/* ================= RECORD BUTTON ================= */

recordBtn.addEventListener("click", async () => {

    if (!isRecording) {
        // ▶ START RECORDING
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);

        audioChunks = [];
        mediaRecorder.start();

        mediaRecorder.ondataavailable = e => audioChunks.push(e.data);

        isRecording = true;
        recordBtn.classList.add("recording");
        status.innerText = "Recording...";
        output.innerText = "";
        startTimer();

    } else {
        // ⏹ STOP RECORDING
        mediaRecorder.stop();
        stopTimer();

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
            const formData = new FormData();
            formData.append("audio", audioBlob);

            status.innerText = "Transcribing...";

            const response = await fetch("/transcribe", {
                method: "POST",
                body: formData
            });

            const result = await response.json();

            output.innerText = result.text;
            status.innerText = "Transcription complete";

            // Enable editing after transcription
            editBtn.disabled = false;
            saveBtn.disabled = true;
        };

        isRecording = false;
        recordBtn.classList.remove("recording");
    }
});

/* ================= EDIT & SAVE FEATURE ================= */

// Enable editing
editBtn.addEventListener("click", () => {
    output.contentEditable = "true";
    output.focus();

    editBtn.disabled = true;
    saveBtn.disabled = false;
    status.innerText = "Edit mode enabled";
});

// Save corrected text
saveBtn.addEventListener("click", () => {
    output.contentEditable = "false";

    editBtn.disabled = false;
    saveBtn.disabled = true;

    const correctedText = output.innerText;
    console.log("Final corrected transcription:", correctedText);

    status.innerText = "Corrections saved";

    // OPTIONAL (future):
    // Send correctedText to backend for saving / re-highlighting
});
