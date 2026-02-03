import motor.motor_asyncio
import os

MONGO_DETAILS = os.getenv("MONGO_DETAILS", "mongodb://localhost:27017")

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_DETAILS)
database = client.clinical_system

doctor_collection = database.get_collection("doctors")
patient_collection = database.get_collection("patients")
consultation_collection = database.get_collection("consultations")
