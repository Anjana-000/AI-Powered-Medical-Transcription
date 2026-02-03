from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from ..database import doctor_collection
from ..models import DoctorModel, Token, DoctorLogin
from ..auth import create_access_token, get_password_hash, verify_password, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()

@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await doctor_collection.find_one({"username": form_data.username})
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", status_code=201)
async def register_doctor(doctor: DoctorModel):
    # Check if exists
    if await doctor_collection.find_one({"username": doctor.username}):
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = get_password_hash(doctor.password)
    doctor_dict = doctor.dict()
    doctor_dict["password"] = hashed_password
    
    new_doctor = await doctor_collection.insert_one(doctor_dict)
    return {"id": str(new_doctor.inserted_id), "msg": "Doctor created successfully"}
