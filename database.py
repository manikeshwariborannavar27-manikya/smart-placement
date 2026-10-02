import os
import logging
from datetime import datetime
from bson import ObjectId
from dotenv import load_dotenv
import pymongo
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SmartPlacementDB")

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
DATABASE_NAME = os.getenv("DATABASE_NAME", "smart_placement")

_client = None
_db = None
_is_mock = False

import socket
from urllib.parse import urlparse

def _is_server_reachable(uri: str) -> bool:
    """Fast probe if MongoDB host:port is reachable."""
    try:
        if uri.startswith("mongodb+srv://"):
            return True
        parsed = urlparse(uri)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 27017
        if host in ["localhost", "127.0.0.1", "0.0.0.0"]:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.1)
            result = s.connect_ex((host, port))
            s.close()
            return result == 0
        else:
            return True
    except Exception:
        return False

def init_db():
    global _client, _db, _is_mock
    if _db is not None:
        return _db

    # Fast probe
    is_reachable = _is_server_reachable(MONGODB_URI)
    if is_reachable:
        try:
            logger.info(f"Connecting to MongoDB at {MONGODB_URI} (DB: {DATABASE_NAME})...")
            client = pymongo.MongoClient(
                MONGODB_URI, 
                serverSelectionTimeoutMS=1500,
                connectTimeoutMS=1500
            )
            client.admin.command('ping')
            _client = client
            _db = _client[DATABASE_NAME]
            _is_mock = False
            logger.info("Successfully connected to live MongoDB instance!")
            _setup_indexes(_db)
            return _db
        except Exception as e:
            logger.warning(f"Live MongoDB ping failed: {e}. Falling back to in-memory mongomock.")
    else:
        logger.info("Local MongoDB port 27017 not active. Utilizing resilient in-memory database.")

    try:
        import mongomock
        _client = mongomock.MongoClient()
        _db = _client[DATABASE_NAME]
        _is_mock = True
        logger.info("Initialized resilient mongomock in-memory database.")
    except ImportError:
        logger.error("mongomock is not installed. Database connection failed.")
        raise RuntimeError("No MongoDB or mongomock available.")

    _setup_indexes(_db)
    return _db

def _setup_indexes(db):
    try:
        # Users unique index
        db.users.create_index("email", unique=True)
        # Students unique index
        db.students.create_index("email", unique=True)
        db.students.create_index("user_id")
        # Placement drives
        db.placement_drives.create_index("company_name")
        # Applications
        db.applications.create_index([("student_id", pymongo.ASCENDING), ("drive_id", pymongo.ASCENDING)])
    except Exception as e:
        logger.debug(f"Index creation note: {e}")

def get_db():
    global _db
    if _db is None:
        return init_db()
    return _db

def get_collection(name: str):
    db = get_db()
    return db[name]

def is_using_mock_db() -> bool:
    global _is_mock
    if _db is None:
        init_db()
    return _is_mock

def get_db_status():
    global _is_mock, _client
    if _db is None:
        init_db()
    return {
        "connected": True,
        "database_name": DATABASE_NAME,
        "mode": "In-Memory Resilient DB (mongomock)" if _is_mock else "Live MongoDB Instance",
        "is_mock": _is_mock,
        "uri": MONGODB_URI if not _is_mock else "In-Memory",
        "collections": [
            "users", "students", "companies", 
            "placement_drives", "applications", 
            "predictions", "recommendations"
        ]
    }

def serialize_doc(doc):
    """Recursively converts ObjectId and datetime to serializable strings."""
    if doc is None:
        return None
    if isinstance(doc, list):
        return [serialize_doc(item) for item in doc]
    if isinstance(doc, dict):
        new_doc = {}
        for k, v in doc.items():
            if isinstance(v, ObjectId):
                new_doc[k] = str(v)
            elif isinstance(v, datetime):
                new_doc[k] = v.isoformat()
            elif isinstance(v, (dict, list)):
                new_doc[k] = serialize_doc(v)
            else:
                new_doc[k] = v
        # Ensure 'id' field is present if '_id' exists
        if '_id' in new_doc and 'id' not in new_doc:
            new_doc['id'] = new_doc['_id']
        return new_doc
    if isinstance(doc, ObjectId):
        return str(doc)
    if isinstance(doc, datetime):
        return doc.isoformat()
    return doc
