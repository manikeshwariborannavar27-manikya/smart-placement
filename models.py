from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime

# ----------------- User Models -----------------
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=4)
    full_name: str
    role: str = Field(default="student", description="Role: 'student' or 'recruiter'")
    company_name: Optional[str] = None
    designation: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: Optional[str] = None
    email: EmailStr
    full_name: str
    role: str
    student_id: Optional[str] = None
    recruiter_id: Optional[str] = None
    company_id: Optional[str] = None
    company_name: Optional[str] = None
    created_at: Optional[str] = None

# ----------------- Recruiter Models -----------------
class RecruiterProfile(BaseModel):
    id: Optional[str] = None
    user_id: Optional[str] = None
    email: EmailStr
    full_name: str
    company_id: Optional[str] = None
    company_name: str
    designation: Optional[str] = "Campus Talent Acquisition / HR"
    phone: Optional[str] = ""
    linkedin_url: Optional[str] = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class RecruiterProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    designation: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    company_name: Optional[str] = None

# ----------------- Student Sub-items -----------------
class ProjectItem(BaseModel):
    title: str
    description: Optional[str] = ""
    technologies: List[str] = []
    github_url: Optional[str] = ""
    live_url: Optional[str] = ""

class CertificationItem(BaseModel):
    title: str
    issuer: str
    issue_date: Optional[str] = ""
    credential_url: Optional[str] = ""

class InternshipItem(BaseModel):
    company_name: str
    role: str
    duration_months: int = 1
    technologies: List[str] = []
    description: Optional[str] = ""

# ----------------- Student Profile -----------------
class StudentProfile(BaseModel):
    id: Optional[str] = None
    user_id: Optional[str] = None
    email: EmailStr
    full_name: str
    roll_no: Optional[str] = ""
    college_name: Optional[str] = ""
    branch: Optional[str] = "Computer Science"
    course: Optional[str] = "B.Tech"
    current_year: Optional[int] = 4
    semester: Optional[int] = 7
    graduation_year: Optional[int] = 2026
    gender: Optional[str] = "Not Specified"
    dob: Optional[str] = ""
    linkedin_url: Optional[str] = ""
    github_url: Optional[str] = ""
    cgpa: float = Field(default=0.0, ge=0.0, le=10.0)
    tenth_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    twelfth_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    quant_score: float = Field(default=0.0, ge=0.0, le=100.0)
    logical_score: float = Field(default=0.0, ge=0.0, le=100.0)
    verbal_score: float = Field(default=0.0, ge=0.0, le=100.0)
    aptitude_score: float = Field(default=0.0, ge=0.0, le=100.0)
    technical_score: float = Field(default=0.0, ge=0.0, le=100.0)
    communication_score: float = Field(default=0.0, ge=0.0, le=100.0)
    skills: List[str] = []
    programming_languages: List[str] = []
    technical_skills: List[str] = []
    soft_skills: List[str] = []
    projects: List[ProjectItem] = []
    certifications: List[CertificationItem] = []
    internships: List[InternshipItem] = []
    backlogs: int = Field(default=0, ge=0)
    target_role: Optional[str] = "Software Engineer"
    bio: Optional[str] = ""
    phone: Optional[str] = ""
    resume_url: Optional[str] = ""
    is_demo: Optional[bool] = False
    updated_at: Optional[str] = None

# ----------------- Company Models -----------------
class CompanyCreate(BaseModel):
    name: str
    industry: str = "Information Technology"
    website: Optional[str] = ""
    contact_email: Optional[str] = ""
    location: Optional[str] = "Bengaluru, India"
    logo_icon: Optional[str] = "🏢"
    description: Optional[str] = ""

class CompanyResponse(CompanyCreate):
    id: Optional[str] = None
    created_at: Optional[str] = None

# ----------------- Placement Drive Models -----------------
class PlacementDriveCreate(BaseModel):
    title: str
    company_name: str
    company_id: Optional[str] = ""
    recruiter_id: Optional[str] = ""
    recruiter_name: Optional[str] = ""
    recruiter_email: Optional[str] = ""
    role: str
    package_lpa: float = Field(..., description="Package in LPA (Lakhs per Annum)")
    min_cgpa: float = Field(default=6.0, ge=0.0, le=10.0)
    required_skills: List[str] = []
    min_aptitude_score: float = Field(default=60.0, ge=0.0, le=100.0)
    max_backlogs: int = Field(default=0, ge=0)
    eligible_branches: List[str] = ["Computer Science", "Information Technology", "Electronics", "Electrical", "Mechanical", "Civil"]
    location: Optional[str] = "Hybrid / Onsite"
    openings: Optional[int] = 10
    logo_icon: Optional[str] = "🏢"
    deadline: Optional[str] = ""
    drive_date: Optional[str] = ""
    status: str = Field(default="Active", description="Active, Upcoming, Closed")
    description: Optional[str] = ""

class PlacementDriveResponse(PlacementDriveCreate):
    id: Optional[str] = None
    created_at: Optional[str] = None
    applicant_count: Optional[int] = 0

class RecruiterStats(BaseModel):
    total_drives: int = 0
    active_drives: int = 0
    total_applications: int = 0
    shortlisted: int = 0
    interview_stage: int = 0
    selected: int = 0
    rejected: int = 0
    company_name: Optional[str] = ""
    candidate_pipeline: Dict[str, int] = {}

# ----------------- Application Models -----------------
class ApplicationStageHistory(BaseModel):
    stage: str
    timestamp: str
    updated_by: Optional[str] = "Admin"
    remarks: Optional[str] = ""

class ApplicationCreate(BaseModel):
    student_id: str
    drive_id: str
    remarks: Optional[str] = ""

class ApplicationStatusUpdate(BaseModel):
    status: str = Field(..., description="Applied, Shortlisted, Aptitude Test, Technical Interview, HR Interview, Selected, Rejected")
    remarks: Optional[str] = ""

class ApplicationResponse(BaseModel):
    id: Optional[str] = None
    student_id: str
    student_name: str
    student_email: str
    roll_no: Optional[str] = ""
    branch: Optional[str] = ""
    cgpa: Optional[float] = 0.0
    drive_id: str
    company_name: str
    role: str
    package_lpa: float
    status: str
    stage_history: List[Dict[str, Any]] = []
    remarks: Optional[str] = ""
    applied_at: Optional[str] = None
    updated_at: Optional[str] = None

# ----------------- Prediction & Eligibility Models -----------------
class EligibilityCheckResult(BaseModel):
    is_eligible: bool
    reasons: List[str]
    missing_criteria: List[str]
    match_percentage: float

class PredictionResult(BaseModel):
    student_id: Optional[str] = None
    student_email: Optional[str] = None
    readiness_score: float
    readiness_category: str  # "High Readiness", "Moderate Readiness", "Needs Improvement"
    estimated_package_range: str
    radar_scores: Dict[str, float]
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    target_role_fit: Dict[str, Any]
    generated_at: str
    disclaimer: str = "This prediction is an estimated readiness assessment based on academic, technical, and extracurricular metrics, not a guaranteed employment outcome."

class RecommendationResponse(BaseModel):
    student_id: str
    target_role: str
    key_strengths: List[str]
    skill_gaps: List[str]
    recommended_skills: List[str]
    recommended_projects: List[Dict[str, Any]]
    recommended_certifications: List[str]
    action_plan: List[str]
