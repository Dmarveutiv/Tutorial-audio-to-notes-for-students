from pymongo import MongoClient
from datetime import datetime


class DBHandler:
    def __init__(self):
        self.client = MongoClient("mongodb://localhost:27017/")
        self.db = self.client["tutorial_notes"]
        self.collection = self.db["sessions"]

    def save_session(self, title, transcript, notes_markdown):
        """Save a completed session to MongoDB"""
        document = {
            "title": title,
            "transcript": transcript,
            "notes_markdown": notes_markdown,
            "created_at": datetime.now()
        }
        result = self.collection.insert_one(document)
        print(f"Session saved to DB with ID: {result.inserted_id}")
        return str(result.inserted_id)

    def get_all_sessions(self):
        """Return all sessions sorted by newest first"""
        sessions = self.collection.find().sort("created_at", -1)
        return list(sessions)

    def get_session_by_id(self, session_id):
        """Return a single session by its MongoDB ID"""
        from bson.objectid import ObjectId
        return self.collection.find_one({"_id": ObjectId(session_id)})

    def delete_session(self, session_id):
        """Delete a session by its MongoDB ID"""
        from bson.objectid import ObjectId
        self.collection.delete_one({"_id": ObjectId(session_id)})
        print(f"Session {session_id} deleted.")