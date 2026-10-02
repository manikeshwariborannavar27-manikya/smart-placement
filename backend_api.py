import os
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from bson import ObjectId
from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.middleware.cors import CORSMiddleware
from auth import hash_password, verify_password

from database import get_db, get_collection, get_db_status, serialize_doc
from models import (
    UserRegister, UserLogin, UserResponse,
    RecruiterProfile, RecruiterProfileUpdate, RecruiterStats,
    StudentProfile, CompanyCreate, CompanyResponse,
    PlacementDriveCreate, PlacementDriveResponse,
    ApplicationCreate, ApplicationStatusUpdate, ApplicationResponse,
    PredictionResult, RecommendationResponse
)
from ml_engine import predictor, EligibilityEvaluator
from seed_data import run_seed

logger = logging.getLogger("SmartPlacementAPI")

app = FastAPI(
    title="PlaceMate - Smart Placement Management & Prediction API",
    description="Backend REST API for placement management, role-based portals (Student, Recruiter, Admin), ML readiness prediction, and application lifecycle tracking.",
    version="2.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    db = get_db()
    if db.users.count_documents({}) == 0:
        logger.info("Database is empty on startup. Initializing demo seed data...")
        run_seed()

# ----------------- Root & Health -----------------
@app.get("/")
def read_root():
    return {
        "service": "PlaceMate - Smart Placement Management & Career Readiness Platform",
        "version": "2.0.0",
        "status": "Online",
        "docs": "/docs"
    }

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "PlaceMate API"}

@app.get("/api/status")
def get_status():
    db_info = get_db_status()
    db = get_db()
    
    counts = {
        "users": db.users.count_documents({}),
        "students": db.students.count_documents({}),
        "recruiters": db.recruiters.count_documents({}),
        "companies": db.companies.count_documents({}),
        "placement_drives": db.placement_drives.count_documents({}),
        "applications": db.applications.count_documents({}),
        "predictions": db.predictions.count_documents({})
    }
    return {
        **db_info,
        "counts": counts
    }

# ----------------- Auth Endpoints -----------------
@app.post("/api/auth/register", response_model=UserResponse)
def register_user(user: UserRegister):
    db = get_db()
    req_role = user.role.lower().strip() if user.role else "student"
    
    if req_role not in ["student", "recruiter", "admin"]:
        req_role = "student"

    existing = db.users.find_one({"email": user.email.lower().strip()})
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists. Please sign in.")

    hashed_pw = hash_password(user.password)
    now = datetime.now().isoformat()
    
    user_doc = {
        "email": user.email.lower().strip(),
        "password_hash": hashed_pw,
        "full_name": user.full_name.strip(),
        "role": req_role,
        "company_name": user.company_name.strip() if user.company_name else None,
        "created_at": now
    }
    result = db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)

    student_id = None
    recruiter_id = None
    company_id = None
    company_name = user.company_name.strip() if user.company_name else None

    # Handle Student Role Setup
    if req_role == "student":
        student_doc = {
            "user_id": user_id,
            "email": user.email.lower().strip(),
            "full_name": user.full_name.strip(),
            "roll_no": "",
            "course": "B.Tech",
            "branch": "Computer Science",
            "semester": 7,
            "graduation_year": 2026,
            "cgpa": 0.0,
            "aptitude_score": 0.0,
            "technical_score": 0.0,
            "communication_score": 0.0,
            "skills": [],
            "programming_languages": [],
            "technical_skills": [],
            "soft_skills": [],
            "projects": [],
            "certifications": [],
            "internships": [],
            "backlogs": 0,
            "target_role": "Software Engineer",
            "bio": "",
            "phone": user.phone or "",
            "linkedin_url": user.linkedin_url or "",
            "resume_url": "",
            "updated_at": now
        }
        st_res = db.students.insert_one(student_doc)
        student_id = str(st_res.inserted_id)

    # Handle Recruiter Role Setup
    elif req_role == "recruiter":
        c_name = company_name or "Partner Organization"
        # Find or create company
        existing_comp = db.companies.find_one({"name": {"$regex": f"^{c_name}$", "$options": "i"}})
        if existing_comp:
            company_id = str(existing_comp["_id"])
            company_name = existing_comp["name"]
        else:
            comp_doc = {
                "name": c_name,
                "industry": "Technology / Services",
                "website": "",
                "contact_email": user.email.lower().strip(),
                "location": "India / Remote",
                "logo_icon": "🏢",
                "description": f"Recruitment portal organization for {c_name}.",
                "created_at": now
            }
            comp_res = db.companies.insert_one(comp_doc)
            company_id = str(comp_res.inserted_id)

        recruiter_doc = {
            "user_id": user_id,
            "email": user.email.lower().strip(),
            "full_name": user.full_name.strip(),
            "company_id": company_id,
            "company_name": company_name,
            "designation": user.designation or "Campus Talent Acquisition Partner",
            "phone": user.phone or "",
            "linkedin_url": user.linkedin_url or "",
            "created_at": now,
            "updated_at": now
        }
        rec_res = db.recruiters.insert_one(recruiter_doc)
        recruiter_id = str(rec_res.inserted_id)

    return UserResponse(
        id=user_id,
        email=user.email.lower().strip(),
        full_name=user.full_name.strip(),
        role=req_role,
        student_id=student_id,
        recruiter_id=recruiter_id,
        company_id=company_id,
        company_name=company_name,
        created_at=now
    )

@app.post("/api/auth/login")
def login_user(creds: UserLogin):
    db = get_db()
    email_clean = creds.email.lower().strip()
    user = db.users.find_one({"email": email_clean})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(creds.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user_role = user.get("role", "student")
    student_id = None
    recruiter_id = None
    company_id = None
    company_name = user.get("company_name")

    if user_role == "student":
        student_profile = db.students.find_one({"email": email_clean})
        if student_profile:
            student_id = str(student_profile["_id"])
    elif user_role == "recruiter":
        recruiter_profile = db.recruiters.find_one({"email": email_clean})
        if recruiter_profile:
            recruiter_id = str(recruiter_profile["_id"])
            company_id = recruiter_profile.get("company_id")
            company_name = recruiter_profile.get("company_name")

    return {
        "success": True,
        "message": "Login successful",
        "user": {
            "id": str(user["_id"]),
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user_role,
            "student_id": student_id,
            "recruiter_id": recruiter_id,
            "company_id": company_id,
            "company_name": company_name
        }
    }

# ----------------- Recruiter Endpoints -----------------

@app.get("/api/recruiter/stats")
def get_recruiter_stats(
    recruiter_id: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    company_name: Optional[str] = Query(None)
):
    db = get_db()
    query = {}
    if recruiter_id and ObjectId.is_valid(recruiter_id):
        query = {"_id": ObjectId(recruiter_id)}
    elif email:
        query = {"email": email.lower().strip()}
    elif company_name:
        query = {"company_name": {"$regex": f"^{company_name}$", "$options": "i"}}

    recruiter = db.recruiters.find_one(query) if query else None
    
    # Determine drives query
    drive_query = {}
    if recruiter:
        c_name = recruiter.get("company_name")
        r_id = str(recruiter["_id"])
        drive_query = {"$or": [{"recruiter_id": r_id}, {"company_name": c_name}]}
    elif company_name:
        drive_query = {"company_name": {"$regex": f"^{company_name}$", "$options": "i"}}

    recruiter_drives = list(db.placement_drives.find(drive_query))
    drive_ids = [str(d["_id"]) for d in recruiter_drives]

    total_drives = len(recruiter_drives)
    active_drives = sum(1 for d in recruiter_drives if d.get("status") == "Active")

    if drive_ids:
        applications = list(db.applications.find({"drive_id": {"$in": drive_ids}}))
    else:
        applications = []

    total_applications = len(applications)
    shortlisted = sum(1 for a in applications if a.get("status") == "Shortlisted")
    interview_stage = sum(1 for a in applications if a.get("status") in ["Aptitude Test", "Technical Interview", "HR Interview"])
    selected = sum(1 for a in applications if a.get("status") == "Selected")
    rejected = sum(1 for a in applications if a.get("status") == "Rejected")

    stages = ["Applied", "Shortlisted", "Aptitude Test", "Technical Interview", "HR Interview", "Selected", "Rejected"]
    candidate_pipeline = {st: sum(1 for a in applications if a.get("status") == st) for st in stages}

    return {
        "total_drives": total_drives,
        "active_drives": active_drives,
        "total_applications": total_applications,
        "shortlisted": shortlisted,
        "interview_stage": interview_stage,
        "selected": selected,
        "rejected": rejected,
        "company_name": recruiter.get("company_name", company_name or ""),
        "candidate_pipeline": candidate_pipeline
    }

@app.get("/api/recruiter/profile/{identifier}")
def get_recruiter_profile(identifier: str):
    db = get_db()
    query = {"email": identifier.lower().strip()}
    if ObjectId.is_valid(identifier):
        query = {"$or": [{"_id": ObjectId(identifier)}, {"user_id": identifier}, {"email": identifier}]}
    
    recruiter = db.recruiters.find_one(query)
    if not recruiter:
        raise HTTPException(status_code=404, detail="Recruiter profile not found")
    return serialize_doc(recruiter)

@app.post("/api/recruiter/profile")
def update_recruiter_profile(data: Dict[str, Any]):
    db = get_db()
    email = data.get("email", "").lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required to update recruiter profile")

    now = datetime.now().isoformat()
    update_data = {k: v for k, v in data.items() if k not in ["_id", "id"]}
    update_data["updated_at"] = now

    db.recruiters.update_one({"email": email}, {"$set": update_data}, upsert=True)
    
    # Also update user's full_name in users collection if provided
    if "full_name" in data:
        db.users.update_one({"email": email}, {"$set": {"full_name": data["full_name"]}})

    saved = db.recruiters.find_one({"email": email})
    return serialize_doc(saved)

@app.get("/api/recruiter/company/{identifier}")
def get_recruiter_company(identifier: str):
    db = get_db()
    query = {"name": {"$regex": f"^{identifier}$", "$options": "i"}}
    if ObjectId.is_valid(identifier):
        query = {"$or": [{"_id": ObjectId(identifier)}, {"name": identifier}]}

    company = db.companies.find_one(query)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return serialize_doc(company)

@app.put("/api/recruiter/company/{company_id}")
def update_recruiter_company(company_id: str, company_data: Dict[str, Any]):
    db = get_db()
    if not ObjectId.is_valid(company_id):
        raise HTTPException(status_code=400, detail="Invalid company ID")

    now = datetime.now().isoformat()
    update_fields = {k: v for k, v in company_data.items() if k not in ["_id", "id"]}
    update_fields["updated_at"] = now

    db.companies.update_one({"_id": ObjectId(company_id)}, {"$set": update_fields})
    updated = db.companies.find_one({"_id": ObjectId(company_id)})
    return serialize_doc(updated)

@app.get("/api/recruiter/drives")
def get_recruiter_drives(
    recruiter_id: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    company_name: Optional[str] = Query(None)
):
    db = get_db()
    query = {}
    if recruiter_id and ObjectId.is_valid(recruiter_id):
        query = {"$or": [{"recruiter_id": recruiter_id}, {"company_name": company_name}]} if company_name else {"recruiter_id": recruiter_id}
    elif email:
        rec = db.recruiters.find_one({"email": email.lower().strip()})
        if rec:
            query = {"$or": [{"recruiter_id": str(rec["_id"])}, {"company_name": rec.get("company_name")}]}
        else:
            query = {"recruiter_email": email.lower().strip()}
    elif company_name:
        query = {"company_name": {"$regex": f"^{company_name}$", "$options": "i"}}

    drives = list(db.placement_drives.find(query).sort("created_at", -1))
    serialized = serialize_doc(drives)
    for d in serialized:
        count = db.applications.count_documents({"drive_id": d["id"]})
        d["applicant_count"] = count
    return serialized

@app.post("/api/recruiter/drives")
def create_recruiter_drive(drive: PlacementDriveCreate):
    db = get_db()
    doc = drive.model_dump()
    doc["created_at"] = datetime.now().isoformat()
    
    # If company_id is missing, look it up by company_name
    if not doc.get("company_id") and doc.get("company_name"):
        comp = db.companies.find_one({"name": {"$regex": f"^{doc['company_name']}$", "$options": "i"}})
        if comp:
            doc["company_id"] = str(comp["_id"])

    res = db.placement_drives.insert_one(doc)
    doc["id"] = str(res.inserted_id)
    doc["applicant_count"] = 0
    return serialize_doc(doc)

@app.get("/api/recruiter/drives/{drive_id}")
def get_recruiter_drive_detail(drive_id: str):
    db = get_db()
    if not ObjectId.is_valid(drive_id):
        raise HTTPException(status_code=400, detail="Invalid drive ID")
    drive = db.placement_drives.find_one({"_id": ObjectId(drive_id)})
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")
    res = serialize_doc(drive)
    res["applicant_count"] = db.applications.count_documents({"drive_id": drive_id})
    return res

@app.put("/api/recruiter/drives/{drive_id}")
def update_recruiter_drive(drive_id: str, update_data: Dict[str, Any]):
    db = get_db()
    if not ObjectId.is_valid(drive_id):
        raise HTTPException(status_code=400, detail="Invalid drive ID")
    
    fields = {k: v for k, v in update_data.items() if k not in ["_id", "id"]}
    fields["updated_at"] = datetime.now().isoformat()
    db.placement_drives.update_one({"_id": ObjectId(drive_id)}, {"$set": fields})
    
    updated = db.placement_drives.find_one({"_id": ObjectId(drive_id)})
    res = serialize_doc(updated)
    res["applicant_count"] = db.applications.count_documents({"drive_id": drive_id})
    return res

@app.patch("/api/recruiter/drives/{drive_id}/toggle-status")
def recruiter_toggle_drive_status(drive_id: str):
    db = get_db()
    if not ObjectId.is_valid(drive_id):
        raise HTTPException(status_code=400, detail="Invalid drive ID")
    drive = db.placement_drives.find_one({"_id": ObjectId(drive_id)})
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")
    new_status = "Inactive" if drive.get("status") == "Active" else "Active"
    db.placement_drives.update_one({"_id": ObjectId(drive_id)}, {"$set": {"status": new_status, "updated_at": datetime.now().isoformat()}})
    drive["status"] = new_status
    res = serialize_doc(drive)
    res["applicant_count"] = db.applications.count_documents({"drive_id": drive_id})
    return res

@app.get("/api/recruiter/drives/{drive_id}/eligible-candidates")
def get_recruiter_drive_candidates(drive_id: str):
    db = get_db()
    if not ObjectId.is_valid(drive_id):
        raise HTTPException(status_code=400, detail="Invalid drive ID")

    drive = db.placement_drives.find_one({"_id": ObjectId(drive_id)})
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")

    students = list(db.students.find({}))
    eligible_candidates = []
    not_eligible_candidates = []

    for s in students:
        eval_res = EligibilityEvaluator.evaluate(s, drive)
        applied = db.applications.find_one({"drive_id": drive_id, "student_id": str(s["_id"])})
        pred = predictor.predict(s)
        
        cand = {
            "id": str(s["_id"]),
            "full_name": s.get("full_name", ""),
            "email": s.get("email", ""),
            "phone": s.get("phone", ""),
            "roll_no": s.get("roll_no", ""),
            "course": s.get("course", "B.Tech"),
            "branch": s.get("branch", ""),
            "semester": s.get("semester", 7),
            "graduation_year": s.get("graduation_year", 2026),
            "cgpa": s.get("cgpa", 0.0),
            "backlogs": s.get("backlogs", 0),
            "skills": s.get("skills", []),
            "resume_url": s.get("resume_url", ""),
            "readiness_score": pred.get("readiness_score", 0.0),
            "readiness_category": pred.get("readiness_category", "Needs Improvement"),
            "has_applied": bool(applied),
            "application_id": str(applied["_id"]) if applied else None,
            "application_status": applied.get("status") if applied else None,
            "applied_at": applied.get("applied_at") if applied else None,
            "eligibility": eval_res
        }

        if eval_res["is_eligible"]:
            eligible_candidates.append(cand)
        else:
            not_eligible_candidates.append(cand)

    return {
        "drive_id": drive_id,
        "drive_title": drive.get("title", ""),
        "company_name": drive.get("company_name", ""),
        "total_evaluated": len(students),
        "eligible_count": len(eligible_candidates),
        "not_eligible_count": len(not_eligible_candidates),
        "eligible": eligible_candidates,
        "not_eligible": not_eligible_candidates
    }

@app.get("/api/recruiter/applications")
def get_recruiter_applications(
    recruiter_id: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    company_name: Optional[str] = Query(None),
    drive_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None)
):
    db = get_db()
    
    if drive_id:
        query = {"drive_id": drive_id}
    else:
        # Find all drives associated with recruiter/company
        d_query = {}
        if recruiter_id and ObjectId.is_valid(recruiter_id):
            d_query = {"$or": [{"recruiter_id": recruiter_id}, {"company_name": company_name}]} if company_name else {"recruiter_id": recruiter_id}
        elif email:
            rec = db.recruiters.find_one({"email": email.lower().strip()})
            if rec:
                d_query = {"$or": [{"recruiter_id": str(rec["_id"])}, {"company_name": rec.get("company_name")}]}
            else:
                d_query = {"recruiter_email": email.lower().strip()}
        elif company_name:
            d_query = {"company_name": {"$regex": f"^{company_name}$", "$options": "i"}}

        drives = list(db.placement_drives.find(d_query))
        drive_ids = [str(d["_id"]) for d in drives]
        query = {"drive_id": {"$in": drive_ids}} if drive_ids else {"drive_id": "none"}

    if status_filter:
        query["status"] = status_filter

    apps = list(db.applications.find(query).sort("applied_at", -1))
    
    # Enrich application with student readiness score
    serialized_apps = serialize_doc(apps)
    for a in serialized_apps:
        if ObjectId.is_valid(a.get("student_id", "")):
            st = db.students.find_one({"_id": ObjectId(a["student_id"])})
            if st:
                pred = predictor.predict(st)
                a["readiness_score"] = pred.get("readiness_score", 0.0)
                a["readiness_category"] = pred.get("readiness_category", "Needs Improvement")
                a["skills"] = st.get("skills", [])
                a["resume_url"] = st.get("resume_url", "")
                a["semester"] = st.get("semester", 7)
                a["graduation_year"] = st.get("graduation_year", 2026)

    return serialized_apps

@app.get("/api/recruiter/candidate/{student_id}")
def get_recruiter_candidate_detail(student_id: str):
    db = get_db()
    query = {"_id": ObjectId(student_id)} if ObjectId.is_valid(student_id) else {"email": student_id}
    student = db.students.find_one(query)
    if not student:
        raise HTTPException(status_code=404, detail="Candidate not found")

    pred = predictor.predict(student)
    
    # Recruiter-safe view of candidate
    candidate_data = {
        "id": str(student["_id"]),
        "full_name": student.get("full_name", ""),
        "email": student.get("email", ""),
        "phone": student.get("phone", ""),
        "roll_no": student.get("roll_no", ""),
        "course": student.get("course", "B.Tech"),
        "branch": student.get("branch", ""),
        "semester": student.get("semester", 7),
        "graduation_year": student.get("graduation_year", 2026),
        "cgpa": student.get("cgpa", 0.0),
        "backlogs": student.get("backlogs", 0),
        "skills": student.get("skills", []),
        "programming_languages": student.get("programming_languages", []),
        "technical_skills": student.get("technical_skills", []),
        "soft_skills": student.get("soft_skills", []),
        "projects": student.get("projects", []),
        "certifications": student.get("certifications", []),
        "internships": student.get("internships", []),
        "resume_url": student.get("resume_url", ""),
        "linkedin_url": student.get("linkedin_url", ""),
        "github_url": student.get("github_url", ""),
        "bio": student.get("bio", ""),
        "readiness": {
            "score": pred.get("readiness_score", 0.0),
            "category": pred.get("readiness_category", "Needs Improvement"),
            "radar_scores": pred.get("radar_scores", {}),
            "strengths": pred.get("strengths", []),
            "target_role_fit": pred.get("target_role_fit", {})
        }
    }
    return candidate_data

@app.patch("/api/recruiter/applications/{app_id}/stage")
def recruiter_update_application_stage(app_id: str, status_update: ApplicationStatusUpdate):
    db = get_db()
    if not ObjectId.is_valid(app_id):
        raise HTTPException(status_code=400, detail="Invalid application ID")

    valid_statuses = [
        "Applied", "Shortlisted", "Aptitude Test", 
        "Technical Interview", "HR Interview", "Selected", "Rejected"
    ]
    if status_update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")

    app_doc = db.applications.find_one({"_id": ObjectId(app_id)})
    if not app_doc:
        raise HTTPException(status_code=404, detail="Application not found")

    now = datetime.now().isoformat()
    history_entry = {
        "stage": status_update.status,
        "timestamp": now,
        "updated_by": "Recruiter",
        "remarks": status_update.remarks or f"Status updated to {status_update.status} by Recruiter"
    }

    db.applications.update_one(
        {"_id": ObjectId(app_id)},
        {
            "$set": {
                "status": status_update.status,
                "remarks": status_update.remarks or app_doc.get("remarks", ""),
                "updated_at": now
            },
            "$push": {
                "stage_history": history_entry
            }
        }
    )

    updated = db.applications.find_one({"_id": ObjectId(app_id)})
    return serialize_doc(updated)

# ----------------- Student Endpoints -----------------
@app.get("/api/students/")
def list_students():
    db = get_db()
    students = list(db.students.find({}))
    return serialize_doc(students)

@app.get("/api/students/{identifier}")
def get_student(identifier: str):
    db = get_db()
    query = {"email": identifier.lower().strip()}
    if ObjectId.is_valid(identifier):
        query = {"$or": [{"_id": ObjectId(identifier)}, {"user_id": identifier}, {"email": identifier}]}
    
    student = db.students.find_one(query)
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")
    return serialize_doc(student)

@app.post("/api/students/profile")
def save_student_profile(profile: StudentProfile):
    db = get_db()
    email = profile.email.lower().strip()
    
    doc = profile.model_dump()
    doc["email"] = email
    doc["updated_at"] = datetime.now().isoformat()
    if "id" in doc:
        del doc["id"]

    existing = db.students.find_one({"email": email})
    if existing:
        db.students.update_one({"email": email}, {"$set": doc})
        saved = db.students.find_one({"email": email})
    else:
        res = db.students.insert_one(doc)
        saved = db.students.find_one({"_id": res.inserted_id})

    # Auto calculate prediction and store it
    try:
        pred = predictor.predict(saved)
        pred["student_id"] = str(saved["_id"])
        pred["student_email"] = email
        db.predictions.update_one(
            {"student_id": str(saved["_id"])},
            {"$set": pred},
            upsert=True
        )
    except Exception as e:
        logger.warning(f"Auto prediction calculation error: {e}")

    return serialize_doc(saved)

# ----------------- Company Endpoints -----------------
@app.get("/api/companies/")
def list_companies():
    db = get_db()
    companies = list(db.companies.find({}))
    serialized = serialize_doc(companies)
    for c in serialized:
        c["drives_count"] = db.placement_drives.count_documents({"company_name": c.get("name")})
    return serialized

@app.post("/api/companies/")
def create_company(company: CompanyCreate):
    db = get_db()
    doc = company.model_dump()
    doc["created_at"] = datetime.now().isoformat()
    res = db.companies.insert_one(doc)
    doc["id"] = str(res.inserted_id)
    return serialize_doc(doc)

# ----------------- Placement Drives Endpoints -----------------
@app.get("/api/drives/")
def list_drives():
    db = get_db()
    drives = list(db.placement_drives.find({}))
    serialized = serialize_doc(drives)
    for d in serialized:
        count = db.applications.count_documents({"drive_id": d["id"]})
        d["applicant_count"] = count
    return serialized

@app.post("/api/drives/")
def create_placement_drive(drive: PlacementDriveCreate):
    db = get_db()
    doc = drive.model_dump()
    doc["created_at"] = datetime.now().isoformat()
    res = db.placement_drives.insert_one(doc)
    doc["id"] = str(res.inserted_id)
    doc["applicant_count"] = 0
    return serialize_doc(doc)

@app.get("/api/drives/{drive_id}")
def get_drive(drive_id: str):
    db = get_db()
    if not ObjectId.is_valid(drive_id):
        raise HTTPException(status_code=400, detail="Invalid drive ID")
    drive = db.placement_drives.find_one({"_id": ObjectId(drive_id)})
    if not drive:
        raise HTTPException(status_code=404, detail="Placement drive not found")
    res = serialize_doc(drive)
    res["applicant_count"] = db.applications.count_documents({"drive_id": drive_id})
    return res

@app.get("/api/drives/{drive_id}/check-eligibility/{student_id}")
def check_student_eligibility(drive_id: str, student_id: str):
    db = get_db()
    if not ObjectId.is_valid(drive_id) or not ObjectId.is_valid(student_id):
        raise HTTPException(status_code=400, detail="Invalid ID format")

    drive = db.placement_drives.find_one({"_id": ObjectId(drive_id)})
    student = db.students.find_one({"_id": ObjectId(student_id)})
    
    if not drive or not student:
        raise HTTPException(status_code=404, detail="Drive or Student not found")

    result = EligibilityEvaluator.evaluate(student, drive)
    return result

@app.get("/api/drives/{drive_id}/eligible-students")
def get_eligible_students_for_drive(drive_id: str):
    db = get_db()
    if not ObjectId.is_valid(drive_id):
        raise HTTPException(status_code=400, detail="Invalid drive ID")

    drive = db.placement_drives.find_one({"_id": ObjectId(drive_id)})
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")

    students = list(db.students.find({}))
    eligible_list = []
    
    for s in students:
        eval_res = EligibilityEvaluator.evaluate(s, drive)
        applied = db.applications.find_one({"drive_id": drive_id, "student_id": str(s["_id"])})
        s_doc = serialize_doc(s)
        s_doc["eligibility"] = eval_res
        s_doc["has_applied"] = bool(applied)
        s_doc["application_status"] = applied.get("status") if applied else None
        eligible_list.append(s_doc)

    return eligible_list

# ----------------- Application Tracking Endpoints -----------------
@app.post("/api/applications/apply")
def apply_to_drive(app_data: ApplicationCreate):
    db = get_db()
    student_id = app_data.student_id
    drive_id = app_data.drive_id

    if not ObjectId.is_valid(student_id) or not ObjectId.is_valid(drive_id):
        raise HTTPException(status_code=400, detail="Invalid Student or Drive ID")

    student = db.students.find_one({"_id": ObjectId(student_id)})
    drive = db.placement_drives.find_one({"_id": ObjectId(drive_id)})

    if not student or not drive:
        raise HTTPException(status_code=404, detail="Student or Drive not found")

    # Check eligibility first
    eval_res = EligibilityEvaluator.evaluate(student, drive)
    if not eval_res["is_eligible"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Candidate is not eligible: {'; '.join(eval_res['missing_criteria'])}"
        )

    # Check duplicate application
    existing = db.applications.find_one({"student_id": student_id, "drive_id": drive_id})
    if existing:
        raise HTTPException(status_code=400, detail="You have already applied for this placement drive")

    now = datetime.now().isoformat()
    app_doc = {
        "student_id": student_id,
        "student_name": student.get("full_name", ""),
        "student_email": student.get("email", ""),
        "roll_no": student.get("roll_no", ""),
        "branch": student.get("branch", ""),
        "cgpa": student.get("cgpa", 0.0),
        "drive_id": drive_id,
        "company_name": drive.get("company_name", ""),
        "role": drive.get("role", ""),
        "package_lpa": drive.get("package_lpa", 0.0),
        "status": "Applied",
        "stage_history": [
            {
                "stage": "Applied",
                "timestamp": now,
                "updated_by": "Student",
                "remarks": app_data.remarks or "Application submitted successfully"
            }
        ],
        "remarks": app_data.remarks or "",
        "applied_at": now,
        "updated_at": now
    }

    res = db.applications.insert_one(app_doc)
    app_doc["id"] = str(res.inserted_id)
    return serialize_doc(app_doc)

@app.get("/api/applications/")
def list_all_applications(status_filter: Optional[str] = None):
    db = get_db()
    query = {}
    if status_filter:
        query["status"] = status_filter
    apps = list(db.applications.find(query).sort("applied_at", -1))
    return serialize_doc(apps)

@app.get("/api/applications/student/{student_id}")
def get_student_applications(student_id: str):
    db = get_db()
    query = {"student_id": student_id}
    if not ObjectId.is_valid(student_id):
        query = {"student_email": student_id}
    apps = list(db.applications.find(query).sort("applied_at", -1))
    return serialize_doc(apps)

@app.get("/api/applications/drive/{drive_id}")
def get_drive_applications(drive_id: str):
    db = get_db()
    apps = list(db.applications.find({"drive_id": drive_id}).sort("applied_at", -1))
    return serialize_doc(apps)

@app.patch("/api/applications/{app_id}/status")
def update_application_status(app_id: str, status_update: ApplicationStatusUpdate):
    db = get_db()
    if not ObjectId.is_valid(app_id):
        raise HTTPException(status_code=400, detail="Invalid application ID")

    valid_statuses = [
        "Applied", "Shortlisted", "Aptitude Test", 
        "Technical Interview", "HR Interview", "Selected", "Rejected"
    ]
    if status_update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")

    app_doc = db.applications.find_one({"_id": ObjectId(app_id)})
    if not app_doc:
        raise HTTPException(status_code=404, detail="Application not found")

    now = datetime.now().isoformat()
    history_entry = {
        "stage": status_update.status,
        "timestamp": now,
        "updated_by": "Admin",
        "remarks": status_update.remarks or f"Status transitioned to {status_update.status}"
    }

    db.applications.update_one(
        {"_id": ObjectId(app_id)},
        {
            "$set": {
                "status": status_update.status,
                "remarks": status_update.remarks or app_doc.get("remarks", ""),
                "updated_at": now
            },
            "$push": {
                "stage_history": history_entry
            }
        }
    )

    updated = db.applications.find_one({"_id": ObjectId(app_id)})
    return serialize_doc(updated)

# ----------------- ML Prediction & Recommendations -----------------
@app.post("/api/predict/readiness")
def predict_readiness(student_data: Dict[str, Any]):
    return predictor.predict(student_data)

@app.get("/api/predict/student/{student_id}")
def get_student_prediction(student_id: str):
    db = get_db()
    query = {"_id": ObjectId(student_id)} if ObjectId.is_valid(student_id) else {"email": student_id}
    student = db.students.find_one(query)
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    pred = predictor.predict(student)
    pred["student_id"] = str(student["_id"])
    pred["student_email"] = student.get("email")
    
    db.predictions.update_one(
        {"student_id": str(student["_id"])},
        {"$set": pred},
        upsert=True
    )
    return pred

@app.get("/api/recommendations/{student_id}")
def get_recommendations(student_id: str):
    db = get_db()
    query = {"_id": ObjectId(student_id)} if ObjectId.is_valid(student_id) else {"email": student_id}
    student = db.students.find_one(query)
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    pred = predictor.predict(student)
    role_fit = pred["target_role_fit"]
    
    sample_projects = [
        {
            "title": f"Production-Ready {role_fit.get('target_role')} Platform",
            "tech_stack": role_fit.get("matched_skills", [])[:2] + role_fit.get("missing_skills", [])[:2],
            "difficulty": "Intermediate-Advanced",
            "impact": "Demonstrates full lifecycle development, caching, and scalable architecture."
        },
        {
            "title": "Real-Time Collaborative Analytics Dashboard",
            "tech_stack": ["WebSockets", "Python", "FastAPI", "React", "Docker"],
            "difficulty": "Advanced",
            "impact": "Highlights asynchronous concurrency, low-latency communication, and modern UI."
        }
    ]

    action_plan = [
        "Week 1: Brush up fundamental data structures (Arrays, Linked Lists, Trees) & solve 20 problems.",
        "Week 2: Deep dive into missing target role skills (" + ", ".join(role_fit.get("missing_skills", [])[:2]) + ").",
        "Week 3: Implement the recommended portfolio project with unit tests and containerized Dockerfile.",
        "Week 4: Conduct 3 mock technical and HR interviews; refine project architecture storytelling."
    ]

    res = {
        "student_id": str(student["_id"]),
        "target_role": role_fit.get("target_role"),
        "key_strengths": pred["strengths"],
        "skill_gaps": role_fit.get("missing_skills", []),
        "recommended_skills": role_fit.get("missing_skills", []),
        "recommended_projects": sample_projects,
        "recommended_certifications": [
            "AWS Certified Cloud Practitioner / Solutions Architect",
            f"Meta Certified {role_fit.get('target_role')} Professional",
            "HashiCorp Certified Terraform Associate"
        ],
        "action_plan": action_plan
    }
    
    db.recommendations.update_one(
        {"student_id": str(student["_id"])},
        {"$set": {**res, "updated_at": datetime.now().isoformat()}},
        upsert=True
    )
    return res

# ----------------- Student Specific Endpoints -----------------
@app.get("/api/student/readiness")
def get_student_readiness_api(student_id: Optional[str] = Query(None), email: Optional[str] = Query(None), target_role: Optional[str] = Query(None)):
    db = get_db()
    query = {}
    if student_id and ObjectId.is_valid(student_id):
        query = {"_id": ObjectId(student_id)}
    elif email:
        query = {"email": email.lower().strip()}
    elif student_id:
        query = {"$or": [{"user_id": student_id}, {"email": student_id}]}
    
    student = db.students.find_one(query) if query else db.students.find_one({})
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    student_copy = dict(student)
    if target_role:
        student_copy["target_role"] = target_role

    pred = predictor.predict(student_copy)
    pred["student_id"] = str(student["_id"])
    pred["student_email"] = student.get("email")
    pred["student_name"] = student.get("full_name") or "Candidate"
    return pred

@app.get("/api/student/drives")
def get_student_drives(student_id: Optional[str] = Query(None)):
    db = get_db()
    drives = list(db.placement_drives.find({}))
    serialized = serialize_doc(drives)
    
    student = None
    if student_id:
        query = {"_id": ObjectId(student_id)} if ObjectId.is_valid(student_id) else {"email": student_id}
        student = db.students.find_one(query)

    for d in serialized:
        count = db.applications.count_documents({"drive_id": d["id"]})
        d["applicant_count"] = count
        if student:
            eval_res = EligibilityEvaluator.evaluate(student, d)
            d["eligibility"] = eval_res
            applied = db.applications.find_one({"drive_id": d["id"], "student_id": str(student["_id"])})
            d["has_applied"] = bool(applied)
            d["application_status"] = applied.get("status") if applied else None
        else:
            d["eligibility"] = {"is_eligible": True, "match_percentage": 100, "missing_criteria": []}
            d["has_applied"] = False
            d["application_status"] = None

    return serialized

@app.get("/api/student/applications")
def get_student_applications_api(student_id: str = Query(...)):
    return get_student_applications(student_id)

@app.post("/api/student/drives/{drive_id}/apply")
def student_apply_drive(drive_id: str, app_data: ApplicationCreate):
    app_data.drive_id = drive_id
    return apply_to_drive(app_data)

# ----------------- Admin Endpoints -----------------
@app.get("/api/admin/stats")
def get_admin_stats():
    db = get_db()
    total_students = db.students.count_documents({})
    total_recruiters = db.recruiters.count_documents({})
    total_companies = db.companies.count_documents({})
    active_drives = db.placement_drives.count_documents({"status": "Active"})
    total_applications = db.applications.count_documents({})
    selected_count = db.applications.count_documents({"status": "Selected"})
    
    students = list(db.students.find({}))
    ready_students = 0
    needs_imp = 0
    for s in students:
        pred = predictor.predict(s)
        if pred["readiness_category"] in ["High Readiness", "Moderate Readiness"]:
            ready_students += 1
        else:
            needs_imp += 1

    placement_pct = round((selected_count / max(1, total_students)) * 100, 1) if total_students > 0 else 0.0

    return {
        "total_students": total_students,
        "total_recruiters": total_recruiters,
        "total_companies": total_companies,
        "active_drives": active_drives,
        "total_applications": total_applications,
        "selected": selected_count,
        "placement_pct": placement_pct,
        "ready_students": ready_students,
        "needs_improvement": needs_imp
    }

@app.get("/api/admin/recruiters")
def get_admin_recruiters():
    db = get_db()
    recruiters = list(db.recruiters.find({}))
    serialized = serialize_doc(recruiters)
    for r in serialized:
        drives_count = db.placement_drives.count_documents({
            "$or": [{"recruiter_id": r["id"]}, {"company_name": r.get("company_name")}]
        })
        r["drives_count"] = drives_count
    return serialized

@app.get("/api/admin/analytics")
def get_admin_analytics():
    db = get_db()
    students = list(db.students.find({}))
    drives = list(db.placement_drives.find({}))
    applications = list(db.applications.find({}))

    # 1. Students by Department
    dept_counts = {}
    for s in students:
        d = s.get("branch", "Other") or "Other"
        dept_counts[d] = dept_counts.get(d, 0) + 1
    students_by_dept = [{"department": k, "count": v} for k, v in dept_counts.items()]

    # 2. Placement by Grad Year
    year_map = {}
    for s in students:
        y = str(s.get("graduation_year", 2026))
        year_map.setdefault(y, {"total": 0, "placed": 0})
        year_map[y]["total"] += 1
    
    for a in applications:
        if a.get("status") == "Selected":
            st_doc = db.students.find_one({"_id": ObjectId(a["student_id"])}) if ObjectId.is_valid(a.get("student_id", "")) else None
            y = str(st_doc.get("graduation_year", 2026)) if st_doc else "2026"
            if y in year_map:
                year_map[y]["placed"] += 1

    placement_by_year = [
        {"year": k, "total": v["total"], "placed": v["placed"]} for k, v in sorted(year_map.items())
    ]

    # 3. CGPA vs Placement
    cgpa_buckets = {"< 6.0": 0, "6.0 - 7.0": 0, "7.0 - 8.0": 0, "8.0 - 9.0": 0, "9.0+": 0}
    cgpa_placed = {"< 6.0": 0, "6.0 - 7.0": 0, "7.0 - 8.0": 0, "8.0 - 9.0": 0, "9.0+": 0}
    for s in students:
        c = float(s.get("cgpa", 0.0))
        if c < 6.0: b = "< 6.0"
        elif c < 7.0: b = "6.0 - 7.0"
        elif c < 8.0: b = "7.0 - 8.0"
        elif c < 9.0: b = "8.0 - 9.0"
        else: b = "9.0+"
        cgpa_buckets[b] += 1
        
        is_sel = db.applications.count_documents({"student_id": str(s["_id"]), "status": "Selected"}) > 0
        if is_sel:
            cgpa_placed[b] += 1

    cgpa_vs_placement = [
        {"bracket": k, "total": cgpa_buckets[k], "placed": cgpa_placed[k]} for k in cgpa_buckets
    ]

    # 4. Most Common Skills
    skill_freq = {}
    for s in students:
        for sk in s.get("skills", []):
            skill_freq[sk] = skill_freq.get(sk, 0) + 1
    most_common_skills = sorted([{"skill": k, "count": v} for k, v in skill_freq.items()], key=lambda x: x["count"], reverse=True)[:10]

    # 5. Company Selections
    comp_selections = {}
    for a in applications:
        if a.get("status") == "Selected":
            c_name = a.get("company_name", "Unknown")
            comp_selections[c_name] = comp_selections.get(c_name, 0) + 1
    company_selections = [{"company": k, "selections": v} for k, v in comp_selections.items()]

    # 6. Readiness Distribution
    readiness_dist = {"High Readiness": 0, "Moderate Readiness": 0, "Needs Improvement": 0}
    for s in students:
        pred = predictor.predict(s)
        cat = pred.get("readiness_category", "Needs Improvement")
        readiness_dist[cat] = readiness_dist.get(cat, 0) + 1

    readiness_list = [{"category": k, "count": v} for k, v in readiness_dist.items()]

    return {
        "students_by_dept": students_by_dept,
        "placement_by_year": placement_by_year,
        "cgpa_vs_placement": cgpa_vs_placement,
        "most_common_skills": most_common_skills,
        "company_selections": company_selections,
        "readiness_distribution": readiness_list
    }

@app.get("/api/admin/students")
def get_admin_students():
    db = get_db()
    students = list(db.students.find({}))
    res = []
    for s in students:
        doc = serialize_doc(s)
        pred = predictor.predict(s)
        doc["readiness_score"] = pred["readiness_score"]
        doc["readiness_category"] = pred["readiness_category"]
        doc["applications_count"] = db.applications.count_documents({"student_id": str(s["_id"])})
        doc["placed"] = db.applications.count_documents({"student_id": str(s["_id"]), "status": "Selected"}) > 0
        res.append(doc)
    return res

@app.get("/api/admin/students/{student_id}")
def get_admin_student_detail(student_id: str):
    db = get_db()
    query = {"_id": ObjectId(student_id)} if ObjectId.is_valid(student_id) else {"email": student_id}
    student = db.students.find_one(query)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    doc = serialize_doc(student)
    pred = predictor.predict(student)
    doc["prediction"] = pred
    doc["applications"] = serialize_doc(list(db.applications.find({"student_id": str(student["_id"])})))
    return doc

@app.get("/api/admin/companies")
def get_admin_companies():
    db = get_db()
    companies = list(db.companies.find({}))
    serialized = serialize_doc(companies)
    for c in serialized:
        c["drives_count"] = db.placement_drives.count_documents({"company_name": c.get("name")})
    return serialized

@app.post("/api/admin/companies")
def post_admin_company(company: CompanyCreate):
    return create_company(company)

@app.delete("/api/admin/companies/{company_id}")
def delete_admin_company(company_id: str):
    db = get_db()
    query = {"_id": ObjectId(company_id)} if ObjectId.is_valid(company_id) else {"id": company_id}
    res = db.companies.delete_one(query)
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Company not found")
    return {"success": True, "message": "Company deleted successfully"}

@app.get("/api/admin/drives")
def get_admin_drives():
    return list_drives()

@app.post("/api/admin/drives")
def post_admin_drive(drive: PlacementDriveCreate):
    return create_placement_drive(drive)

@app.patch("/api/admin/drives/{drive_id}/toggle-status")
def toggle_drive_status(drive_id: str):
    db = get_db()
    if not ObjectId.is_valid(drive_id):
        raise HTTPException(status_code=400, detail="Invalid drive ID")
    drive = db.placement_drives.find_one({"_id": ObjectId(drive_id)})
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")
    new_status = "Inactive" if drive.get("status") == "Active" else "Active"
    db.placement_drives.update_one({"_id": ObjectId(drive_id)}, {"$set": {"status": new_status, "updated_at": datetime.now().isoformat()}})
    drive["status"] = new_status
    return serialize_doc(drive)

@app.get("/api/admin/drives/{drive_id}/eligible")
def get_admin_drive_eligible(drive_id: str):
    return get_eligible_students_for_drive(drive_id)

@app.patch("/api/admin/applications/{app_id}/stage")
def update_application_stage(app_id: str, status_update: ApplicationStatusUpdate):
    return update_application_status(app_id, status_update)

@app.get("/api/admin/export/students.csv")
def export_students_csv():
    from fastapi.responses import Response
    import io
    import csv

    db = get_db()
    students = list(db.students.find({}))
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        "Full Name", "Email", "Phone", "Roll Number", "Department",
        "Graduation Year", "CGPA", "Backlogs", "Aptitude Score",
        "Technical Score", "Communication Score", "Readiness Score",
        "Readiness Category", "Placed", "Skills", "LinkedIn URL"
    ])
    
    for s in students:
        pred = predictor.predict(s)
        is_placed = "Yes" if db.applications.count_documents({"student_id": str(s["_id"]), "status": "Selected"}) > 0 else "No"
        writer.writerow([
            s.get("full_name", ""),
            s.get("email", ""),
            s.get("phone", ""),
            s.get("roll_no", ""),
            s.get("branch", ""),
            s.get("graduation_year", 2026),
            s.get("cgpa", 0.0),
            s.get("backlogs", 0),
            s.get("aptitude_score", 0.0),
            s.get("technical_score", 0.0),
            s.get("communication_score", 0.0),
            pred.get("readiness_score", 0.0),
            pred.get("readiness_category", "Needs Improvement"),
            is_placed,
            "; ".join(s.get("skills", [])),
            s.get("linkedin_url", "")
        ])
        
    csv_content = output.getvalue()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=students.csv"}
    )

# ----------------- Demo / Seed Data Endpoint -----------------
@app.post("/api/seed")
def seed_database():
    return run_seed()
