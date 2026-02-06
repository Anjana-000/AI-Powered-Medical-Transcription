from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

class DoctorModel(BaseModel):
    name: str = Field(...)
    username: str = Field(...)
    password: str = Field(...)

class DoctorLogin(BaseModel):
    username: str = Field(...)
    password: str = Field(...)

class PatientModel(BaseModel):
    doctor_id: str = Field(...)
    name: str = Field(...)
    age: int = Field(...)
    gender: str = Field(...)
    contact: str = Field(...)
    medical_history: Optional[str] = None
    address: Optional[str] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    sleeping_hours: Optional[str] = None

class PatientUpdateModel(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    contact: Optional[str] = None
    medical_history: Optional[str] = None
    address: Optional[str] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    sleeping_hours: Optional[str] = None

class PatientResponse(PatientModel):
    id: str

class ConsultationModel(BaseModel):
    patient_id: str = Field(...)
    doctor_id: str = Field(...)
    date: datetime = Field(default_factory=datetime.utcnow)
    transcription_text: Optional[str] = None
    prescription_notes: Optional[str] = None
    audio_filename: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str
