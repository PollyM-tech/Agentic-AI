"""
MongoDB Database Helper for JAC-GPT Chat Sessions
Provides database operations for storing and retrieving chat sessions.
"""

import os
import pymongo
from pymongo import MongoClient
from datetime import datetime
from typing import List, Dict, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global database instance
_database_instance = None

class MongoDB:
    """MongoDB connection and operations handler for chat sessions."""
    
    def __init__(self):
        """Initialize MongoDB connection."""
        self.client = None
        self.db = None
        self.sessions_collection = None
        self.messages_collection = None
        self.connect()
    
    def connect(self):
        """Establish connection to MongoDB."""
        try:
            print("🔄 [DEBUG] Starting MongoDB connection...")
            
            # Get MongoDB connection string from environment
            mongo_uri = os.getenv("MONGODB_URI")
            if not mongo_uri:
                print("❌ [DEBUG] MONGODB_URI not found! Falling back to localhost...")
                mongo_uri = "mongodb://localhost:27017/"
            
            print(f"✅ [DEBUG] Using connection string: {mongo_uri[:30]}...")
            
            db_name = os.getenv("MONGODB_DATABASE", "jac_gpt")
            print(f"✅ [DEBUG] Using database: {db_name}")
            
            # Create connection
            self.client = MongoClient(mongo_uri)
            self.db = self.client[db_name]
            
            # Get collections
            self.sessions = self.db.sessions
            self.messages = self.db.messages
            
            print(f"✅ [DEBUG] Collections initialized: sessions, messages")
            
            # Test connection
            self.client.admin.command('ping')
            print("✅ [DEBUG] MongoDB connection test successful!")
            logger.info(f"Connected to MongoDB: {db_name}")
            
        except Exception as e:
            print(f"❌ [DEBUG] Failed to connect to MongoDB: {e}")
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    def create_session(self, session_id: str) -> dict:
        """Create a new session in the database."""
        try:
            print(f"🔄 [DEBUG] Creating session: {session_id}")
            session_data = {
                "_id": session_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "status": "active"
            }
            
            # Check if session already exists
            existing = self.sessions.find_one({"_id": session_id})
            if existing:
                print(f"✅ [DEBUG] Session {session_id} already exists")
                logger.info(f"Session {session_id} already exists")
                return existing
            
            result = self.sessions.insert_one(session_data)
            print(f"✅ [DEBUG] Created new session: {session_id}, Insert ID: {result.inserted_id}")
            logger.info(f"Created new session: {session_id}")
            return session_data
            
        except Exception as e:
            print(f"❌ [DEBUG] Error creating session {session_id}: {e}")
            logger.error(f"Error creating session {session_id}: {e}")
            return None
    
    def get_session(self, session_id: str) -> dict:
        """Get session data from the database."""
        try:
            print(f"🔍 [DEBUG] Looking for session: {session_id}")
            session = self.sessions.find_one({"_id": session_id})
            if session:
                print(f"✅ [DEBUG] Found session: {session_id}")
            else:
                print(f"❌ [DEBUG] Session not found: {session_id}")
            return session
        except Exception as e:
            print(f"❌ [DEBUG] Error getting session {session_id}: {e}")
            logger.error(f"Error getting session {session_id}: {e}")
            return None

    def save_message(self, session_id: str, role: str, content: str) -> bool:
        """Save a message to the database."""
        try:
            print(f"🔄 [DEBUG] Saving message for session {session_id}, role: {role}")
            print(f"📝 [DEBUG] Message content preview: {content[:100]}...")
            
            message_data = {
                "session_id": session_id,
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow()
            }
            
            result = self.messages.insert_one(message_data)
            print(f"✅ [DEBUG] Message saved with ID: {result.inserted_id}")
            
            # Update session's updated_at timestamp
            update_result = self.sessions.update_one(
                {"_id": session_id},
                {"$set": {"updated_at": datetime.utcnow()}}
            )
            print(f"✅ [DEBUG] Session timestamp updated, modified count: {update_result.modified_count}")
            
            logger.info(f"Saved {role} message for session {session_id}")
            return True
            
        except Exception as e:
            print(f"❌ [DEBUG] Error saving message for session {session_id}: {e}")
            logger.error(f"Error saving message for session {session_id}: {e}")
            return False
    
    def get_chat_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Retrieve chat history for a session."""
        try:
            messages = list(
                self.messages.find(
                    {"session_id": session_id}
                ).sort("timestamp", 1).limit(limit)
            )
            
            # Convert ObjectId to string and format for chat history
            chat_history = []
            for msg in messages:
                chat_history.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            return chat_history
            
        except Exception as e:
            logger.error(f"Error retrieving chat history for session {session_id}: {e}")
            return []
    
    def get_session_stats(self, session_id: str) -> Dict:
        """Get statistics for a session."""
        try:
            session = self.get_session(session_id)
            if not session:
                return {}
            
            message_count = self.messages.count_documents({"session_id": session_id})
            user_messages = self.messages.count_documents({
                "session_id": session_id, 
                "role": "user"
            })
            assistant_messages = self.messages.count_documents({
                "session_id": session_id, 
                "role": "assistant"
            })
            
            return {
                "session_id": session_id,
                "total_messages": message_count,
                "user_messages": user_messages,
                "assistant_messages": assistant_messages,
                "created_at": session["created_at"],
                "updated_at": session["updated_at"]
            }
            
        except Exception as e:
            logger.error(f"Error getting session stats for {session_id}: {e}")
            return {}
    
    def close_session(self, session_id: str):
        """Mark a session as closed."""
        try:
            self.sessions.update_one(
                {"_id": session_id},
                {
                    "$set": {
                        "status": "closed",
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            logger.info(f"Closed session: {session_id}")
            
        except Exception as e:
            logger.error(f"Error closing session {session_id}: {e}")
    
    def close_connection(self):
        """Close the MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")

# Global database instance
_db_instance = None

def get_database() -> MongoDB:
    """Get database instance."""
    global _database_instance
    if _database_instance is None:
        print("🔄 [DEBUG] Creating new database instance...")
        _database_instance = MongoDB()
        print("✅ [DEBUG] Database instance created successfully!")
    else:
        print("✅ [DEBUG] Using existing database instance")
    return _database_instance

def close_database():
    """Close the global database connection."""
    global _db_instance
    if _db_instance:
        _db_instance.close_connection()
        _db_instance = None
