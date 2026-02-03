from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import List, Optional
from ..database import consultation_collection
from ..models import ConsultationModel
from ..auth import get_current_user
from bson import ObjectId
from datetime import datetime

router = APIRouter()

def consultation_helper(consultation) -> dict:
    return {
        "id": str(consultation["_id"]),
        "patient_id": consultation["patient_id"],
        "doctor_id": consultation["doctor_id"],
        "date": consultation["date"],
        "transcription_text": consultation.get("transcription_text"),
        "prescription_notes": consultation.get("prescription_notes"),
    }

@router.get("/{patient_id}")
async def get_consultations(patient_id: str, current_user: dict = Depends(get_current_user)):
    consultations = []
    async for consultation in consultation_collection.find({"patient_id": patient_id}):
        consultations.append(consultation_helper(consultation))
    return consultations

@router.post("/")
async def create_consultation(
    patient_id: str = Form(...),
    prescription_notes: Optional[str] = Form(None),
    audio: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    doctor_id = str(current_user["_id"])
    
    transcription = ""
    if audio:
        # Save temp file
        file_location = f"temp_{audio.filename}"
        with open(file_location, "wb+") as file_object:
            content = await audio.read()
            file_object.write(content)
            
        # ============================================================
        # TODO: Integrate Whisper transcription function here
        # ============================================================
        # Example Integration:
        # from ...services.whisper_service import transcribe_audio
        # transcription = transcribe_audio(file_location)
        # ============================================================
        
        # Placeholder behavior
        transcription = "Transcription pending integration..."
        
        # Cleanup
        import os
        if os.path.exists(file_location):
            os.remove(file_location)
    
    consultation_dict = {
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "date": datetime.utcnow(),
        "transcription_text": transcription,
        "prescription_notes": prescription_notes
    }
    
    new_consultation = await consultation_collection.insert_one(consultation_dict)
    return {"id": str(new_consultation.inserted_id), "transcription": transcription}
