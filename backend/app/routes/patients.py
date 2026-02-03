from fastapi import APIRouter, Depends, HTTPException
from typing import List
from ..database import patient_collection
from ..models import PatientModel, PatientResponse
from ..auth import get_current_user
from bson import ObjectId

router = APIRouter()

def patient_helper(patient) -> dict:
    return {
        "id": str(patient["_id"]),
        "doctor_id": patient["doctor_id"],
        "name": patient["name"],
        "age": patient["age"],
        "gender": patient["gender"],
        "contact": patient["contact"],
        "medical_history": patient.get("medical_history", "")
    }

@router.get("/", response_model=List[PatientResponse])
async def get_patients(current_user: dict = Depends(get_current_user)):
    patients = []
    # Only show patients for this doctor
    # current_user is the doctor dict from DB
    doctor_id = str(current_user["_id"])
    async for patient in patient_collection.find({"doctor_id": doctor_id}):
        patients.append(patient_helper(patient))
    return patients

@router.post("/", response_model=PatientResponse)
async def add_patient(patient: PatientModel, current_user: dict = Depends(get_current_user)):
    # Enforce doctor_id from token
    patient.doctor_id = str(current_user["_id"])
    patient_dict = patient.dict()
    new_patient = await patient_collection.insert_one(patient_dict)
    created_patient = await patient_collection.find_one({"_id": new_patient.inserted_id})
    return patient_helper(created_patient)

@router.get("/{id}", response_model=PatientResponse)
async def get_patient(id: str, current_user: dict = Depends(get_current_user)):
    patient = await patient_collection.find_one({"_id": ObjectId(id)})
    if patient:
        # Check authorization (optional: if patients are strictly private)
        if patient["doctor_id"] != str(current_user["_id"]):
             raise HTTPException(status_code=403, detail="Not authorized to view this patient")
        return patient_helper(patient)
    raise HTTPException(status_code=404, detail="Patient not found")
