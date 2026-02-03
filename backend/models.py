from flask_login import UserMixin
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import uuid

class Doctor(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data.get('_id'))
        self.username = user_data.get('username')
        self.email = user_data.get('email')

    @staticmethod
    def get(mongo, user_id):
        user_data = mongo.db.doctors.find_one({"_id": ObjectId(user_id)})
        if user_data:
            return Doctor(user_data)
        return None

    @staticmethod
    def find_by_username(mongo, username):
        user_data = mongo.db.doctors.find_one({"username": username})
        if user_data:
            return Doctor(user_data)
        return None

    @staticmethod
    def create_user(mongo, username, password_hash, email):
        return mongo.db.doctors.insert_one({
            "username": username,
            "password": password_hash,
            "email": email
        })

class Patient:
    @staticmethod
    def create(mongo, data):
        data['created_at'] = datetime.utcnow()
        data['consultations'] = []
        data['files'] = []
        return mongo.db.patients.insert_one(data)

    @staticmethod
    def get_all(mongo):
        return list(mongo.db.patients.find().sort("created_at", -1))

    @staticmethod
    def get_by_id(mongo, patient_id):
        try:
            patient = mongo.db.patients.find_one({"_id": ObjectId(patient_id)})
            if patient and 'consultations' in patient:
                updated = False
                for c in patient['consultations']:
                    if 'id' not in c:
                        c['id'] = uuid.uuid4().hex
                        updated = True
                if updated:
                     mongo.db.patients.update_one({"_id": ObjectId(patient_id)}, {"$set": {"consultations": patient['consultations']}})
            return patient
        except:
            return None

    @staticmethod
    def search(mongo, query):
        rgx = {"$regex": query, "$options": "i"}
        return list(mongo.db.patients.find({
            "$or": [
                {"name": rgx},
                {"health_id": rgx} # Assuming a health ID field might exist or just name
            ]
        }))

    @staticmethod
    def add_consultation(mongo, patient_id, consultation_data):
        return mongo.db.patients.update_one(
            {"_id": ObjectId(patient_id)},
            {"$push": {"consultations": consultation_data}}
        )

    @staticmethod
    def delete_consultation(mongo, patient_id, consultation_id):
        return mongo.db.patients.update_one(
            {"_id": ObjectId(patient_id)},
            {"$pull": {"consultations": {"id": consultation_id}}}
        )

    @staticmethod
    def add_file(mongo, patient_id, file_data):
        return mongo.db.patients.update_one(
            {"_id": ObjectId(patient_id)},
            {"$push": {"files": file_data}}
        )

    @staticmethod
    def update(mongo, patient_id, data):
         return mongo.db.patients.update_one(
            {"_id": ObjectId(patient_id)},
            {"$set": data}
        )
