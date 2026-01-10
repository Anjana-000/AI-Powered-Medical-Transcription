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
        if (window.enablePostActions) window.enablePostActions();


        status.innerText = "Transcription complete";

        startBtn.disabled = false;
        stopBtn.disabled = true;
    };
});
// =======================
// POST-TRANSCRIPTION ACTIONS
// =======================

const editBtn = document.getElementById("editBtn");
const copyBtn = document.getElementById("copyBtn");
const shareBtn = document.getElementById("shareBtn");
const pdfBtn = document.getElementById("pdfBtn");

const shareMenu = document.getElementById("shareMenu");
const shareWhatsapp = document.getElementById("shareWhatsapp");
const shareGmail = document.getElementById("shareGmail");
const shareSystem = document.getElementById("shareSystem");

// SAFETY GUARD (prevents breaking other pages)
if (editBtn && copyBtn && shareBtn && pdfBtn && output) {

    // 🔑 Enable buttons after transcription
    window.enablePostActions = function () {
        editBtn.disabled = false;
        copyBtn.disabled = false;
        shareBtn.disabled = false;
        pdfBtn.disabled = false;
    };

    // ✏️ Edit
    editBtn.addEventListener("click", () => {
        const isEditable = output.contentEditable === "true";
        output.contentEditable = (!isEditable).toString();
        editBtn.innerText = isEditable ? "Edit" : "Lock";
        output.focus();
    });

    // 📋 Copy
    copyBtn.addEventListener("click", () => {
        navigator.clipboard.writeText(output.innerText);
        alert("Copied to clipboard");
    });

    // 🔽 Share menu toggle
    shareBtn.addEventListener("click", () => {
        shareMenu.style.display =
            shareMenu.style.display === "block" ? "none" : "block";
    });

    // 💬 WhatsApp
    shareWhatsapp.addEventListener("click", () => {
        window.open(
            `https://wa.me/?text=${encodeURIComponent(output.innerText)}`,
            "_blank"
        );
        shareMenu.style.display = "none";
    });

    // 📧 Gmail
    shareGmail.addEventListener("click", () => {
        window.open(
            `https://mail.google.com/mail/?view=cm&fs=1&body=${encodeURIComponent(output.innerText)}`,
            "_blank"
        );
        shareMenu.style.display = "none";
    });

    // 🔗 System share (Bluetooth / Nearby / etc.)
    shareSystem.addEventListener("click", async () => {
        if (navigator.share) {
            await navigator.share({
                title: "Medical Transcription",
                text: output.innerText
            });
        } else {
            alert("System sharing not supported on this browser");
        }
        shareMenu.style.display = "none";
    });

    // 📄 PDF
    pdfBtn.addEventListener("click", () => {
        const doc = new window.jspdf.jsPDF();
        doc.text(output.innerText, 10, 10);
        doc.save("Medical_Transcription.pdf");
    });

    // Close share menu when clicking outside
    document.addEventListener("click", (e) => {
        if (!shareBtn.contains(e.target) && !shareMenu.contains(e.target)) {
            shareMenu.style.display = "none";
        }
    });
}
