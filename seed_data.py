import logging
from datetime import datetime
from auth import hash_password
from database import get_db, serialize_doc
from ml_engine import predictor

logger = logging.getLogger("SmartPlacementSeeder")

def run_seed():
    db = get_db()
    
    # Check if data already exists
    if db.users.count_documents({}) > 0 and db.placement_drives.count_documents({}) > 0:
        return {"success": True, "message": "Database already contains data.", "seeded": False}

    logger.info("Seeding initial demo data for Hackathon evaluation...")

    # 1. Seed Companies first to obtain company IDs
    companies_to_seed = [
        {"name": "Google", "industry": "Technology / Cloud / AI", "website": "https://google.com", "contact_email": "campus-recruitment@google.com", "location": "Bengaluru / Hyderabad", "logo_icon": "🌐", "description": "Global technology leader in search, cloud systems, and AI innovation.", "created_at": datetime.now().isoformat()},
        {"name": "Microsoft", "industry": "Enterprise Software & Cloud", "website": "https://microsoft.com", "contact_email": "university-hiring@microsoft.com", "location": "Hyderabad / Noida", "logo_icon": "💻", "description": "Global platform company empowering individuals and organizations with cloud & software.", "created_at": datetime.now().isoformat()},
        {"name": "Amazon", "industry": "E-Commerce & Cloud Computing", "website": "https://amazon.jobs", "contact_email": "campus-india@amazon.com", "location": "Bengaluru / Hyderabad", "logo_icon": "📦", "description": "Customer obsessed world leader in e-commerce, cloud computing (AWS), and logistics.", "created_at": datetime.now().isoformat()},
        {"name": "Goldman Sachs", "industry": "Financial Technology & Investment", "website": "https://goldmansachs.com", "contact_email": "campusrecruiting@gs.com", "location": "Bengaluru", "logo_icon": "📈", "description": "Premier global financial institution leveraging cutting edge financial engineering & tech.", "created_at": datetime.now().isoformat()},
        {"name": "Infosys", "industry": "IT Consulting & Services", "website": "https://infosys.com", "contact_email": "talent@infosys.com", "location": "Bengaluru / Pune", "logo_icon": "🏛️", "description": "Global leader in next-generation digital services and consulting.", "created_at": datetime.now().isoformat()}
    ]

    company_ids = {}
    for comp in companies_to_seed:
        db.companies.update_one({"name": comp["name"]}, {"$set": comp}, upsert=True)
        found = db.companies.find_one({"name": comp["name"]})
        company_ids[comp["name"]] = str(found["_id"])

    # 2. Seed Users (Admin, Recruiters, Students)
    admin_pw = hash_password("admin123")
    recruiter_pw = hash_password("recruiter123")
    student_pw = hash_password("student123")

    users_to_seed = [
        {"email": "admin@placement.edu", "password_hash": admin_pw, "full_name": "Placement Director Dr. Sharma", "role": "admin", "created_at": datetime.now().isoformat()},
        {"email": "recruiter@google.com", "password_hash": recruiter_pw, "full_name": "Sundar Raman", "role": "recruiter", "company_name": "Google", "created_at": datetime.now().isoformat()},
        {"email": "hiring@microsoft.com", "password_hash": recruiter_pw, "full_name": "Anjali Rao", "role": "recruiter", "company_name": "Microsoft", "created_at": datetime.now().isoformat()},
        {"email": "rahul.sharma@college.edu", "password_hash": student_pw, "full_name": "Rahul Sharma", "role": "student", "created_at": datetime.now().isoformat()},
        {"email": "priya.patel@college.edu", "password_hash": student_pw, "full_name": "Priya Patel", "role": "student", "created_at": datetime.now().isoformat()},
        {"email": "amit.kumar@college.edu", "password_hash": student_pw, "full_name": "Amit Kumar", "role": "student", "created_at": datetime.now().isoformat()},
        {"email": "ananya.verma@college.edu", "password_hash": student_pw, "full_name": "Ananya Verma", "role": "student", "created_at": datetime.now().isoformat()},
    ]

    user_ids = {}
    for u in users_to_seed:
        db.users.update_one({"email": u["email"]}, {"$set": u}, upsert=True)
        found = db.users.find_one({"email": u["email"]})
        user_ids[u["email"]] = str(found["_id"])

    # 3. Seed Recruiters Collection
    recruiters_to_seed = [
        {
            "user_id": user_ids["recruiter@google.com"],
            "email": "recruiter@google.com",
            "full_name": "Sundar Raman",
            "company_id": company_ids["Google"],
            "company_name": "Google",
            "designation": "Staff University Recruiter & Talent Lead",
            "phone": "+91 9876543220",
            "linkedin_url": "https://linkedin.com/in/sundar-recruiter-google",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        },
        {
            "user_id": user_ids["hiring@microsoft.com"],
            "email": "hiring@microsoft.com",
            "full_name": "Anjali Rao",
            "company_id": company_ids["Microsoft"],
            "company_name": "Microsoft",
            "designation": "Lead Campus Talent Partner",
            "phone": "+91 9876543221",
            "linkedin_url": "https://linkedin.com/in/anjali-recruiter-msft",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    ]

    recruiter_ids = {}
    for rec in recruiters_to_seed:
        db.recruiters.update_one({"email": rec["email"]}, {"$set": rec}, upsert=True)
        found = db.recruiters.find_one({"email": rec["email"]})
        recruiter_ids[rec["email"]] = str(found["_id"])

    # 2. Seed Students
    students_to_seed = [
        {
            "user_id": user_ids["rahul.sharma@college.edu"],
            "email": "rahul.sharma@college.edu",
            "full_name": "Rahul Sharma",
            "roll_no": "22CS101",
            "course": "B.Tech",
            "branch": "Computer Science",
            "semester": 7,
            "graduation_year": 2026,
            "gender": "Male",
            "dob": "2004-06-15",
            "cgpa": 8.75,
            "aptitude_score": 85.0,
            "technical_score": 88.0,
            "communication_score": 82.0,
            "skills": ["Python", "FastAPI", "React", "PostgreSQL", "Data Structures", "Git", "Docker", "Problem Solving", "Team Leadership"],
            "programming_languages": ["Python", "JavaScript", "C++", "SQL"],
            "technical_skills": ["FastAPI", "React", "Docker", "PostgreSQL", "Data Structures", "Git"],
            "soft_skills": ["Problem Solving", "Team Leadership", "Effective Communication", "Adaptability"],
            "projects": [
                {"title": "AI Resume Screener", "description": "NLP tool parsing PDF resumes and ranking them by job description similarity.", "technologies": ["Python", "FastAPI", "SpaCy", "React"], "github_url": "https://github.com/rahul/resume-screener"},
                {"title": "Distributed Task Scheduler", "description": "Fault-tolerant queue scheduler handling microservice jobs.", "technologies": ["Go", "Redis", "Docker"], "github_url": "https://github.com/rahul/task-scheduler"}
            ],
            "certifications": [
                {"title": "AWS Certified Cloud Practitioner", "issuer": "Amazon Web Services", "issue_date": "2025-08-15", "credential_url": "https://aws.amazon.com/verify/123"},
                {"title": "Meta Frontend Developer Specialization", "issuer": "Coursera", "issue_date": "2025-03-10", "credential_url": "https://coursera.org/verify/456"}
            ],
            "internships": [
                {"company_name": "TechSprint Labs", "role": "Backend Engineering Intern", "duration_months": 3, "description": "Built REST APIs for 100k daily active users and improved query latency by 35%."}
            ],
            "backlogs": 0,
            "target_role": "Full Stack Developer",
            "bio": "Aspiring Full Stack Engineer passionate about scalable distributed systems and modern web frameworks.",
            "phone": "+91 9876543210",
            "linkedin_url": "https://www.linkedin.com/in/demo-candidate",
            "github_url": "https://github.com/demo-candidate",
            "resume_url": "https://drive.google.com/file/d/demo_resume/view",
            "is_demo": True,
            "updated_at": datetime.now().isoformat()
        },
        {
            "user_id": user_ids["priya.patel@college.edu"],
            "email": "priya.patel@college.edu",
            "full_name": "Priya Patel",
            "roll_no": "22CS102",
            "course": "B.Tech",
            "branch": "Computer Science",
            "semester": 7,
            "graduation_year": 2026,
            "gender": "Female",
            "dob": "2004-03-22",
            "cgpa": 9.20,
            "aptitude_score": 92.0,
            "technical_score": 94.0,
            "communication_score": 89.0,
            "skills": ["Python", "Machine Learning", "TensorFlow", "Pandas", "NumPy", "SQL", "Scikit-Learn", "AWS", "Analytical Thinking", "Presentation"],
            "programming_languages": ["Python", "R", "SQL", "C++"],
            "technical_skills": ["Machine Learning", "TensorFlow", "Pandas", "NumPy", "Scikit-Learn", "AWS Cloud"],
            "soft_skills": ["Analytical Thinking", "Presentation Skills", "Research & Innovation", "Teamwork"],
            "projects": [
                {"title": "Brain Tumor MRI Segmentation", "description": "Deep learning convolutional neural network achieving 94% dice coefficient.", "technologies": ["Python", "PyTorch", "OpenCV"], "github_url": "https://github.com/priya/mri-seg"},
                {"title": "Financial Fraud Detector", "description": "Real-time anomaly detection pipeline on streaming transaction data.", "technologies": ["Python", "Kafka", "Scikit-Learn"], "github_url": "https://github.com/priya/fraud-det"}
            ],
            "certifications": [
                {"title": "Deep Learning Specialization", "issuer": "DeepLearning.AI", "issue_date": "2025-06-12", "credential_url": "https://deeplearning.ai/verify"}
            ],
            "internships": [
                {"company_name": "NeuroHealth Analytics", "role": "Data Science Intern", "duration_months": 6, "description": "Trained predictive patient outcome models and deployed them via FastAPI microservices."}
            ],
            "backlogs": 0,
            "target_role": "Data Scientist / AI Engineer",
            "bio": "Passionate AI & Data Science researcher looking to build ethical and transformative machine intelligence.",
            "phone": "+91 9876543211",
            "resume_url": "https://drive.google.com/file/d/priya_resume_2026/view",
            "updated_at": datetime.now().isoformat()
        },
        {
            "user_id": user_ids["amit.kumar@college.edu"],
            "email": "amit.kumar@college.edu",
            "full_name": "Amit Kumar",
            "roll_no": "22IT103",
            "course": "B.Tech",
            "branch": "Information Technology",
            "semester": 7,
            "graduation_year": 2026,
            "gender": "Male",
            "dob": "2004-09-10",
            "cgpa": 6.80,
            "aptitude_score": 62.0,
            "technical_score": 65.0,
            "communication_score": 70.0,
            "skills": ["Java", "SQL", "HTML/CSS", "JavaScript", "C++", "Time Management"],
            "programming_languages": ["Java", "C++", "JavaScript", "SQL"],
            "technical_skills": ["Spring Boot", "MySQL", "HTML/CSS", "Git"],
            "soft_skills": ["Time Management", "Dedication", "Active Listening"],
            "projects": [
                {"title": "Online Book Library Management", "description": "CRUD web application for library cataloging and user borrowing records.", "technologies": ["Java", "Spring Boot", "MySQL"], "github_url": "https://github.com/amit/library-mgmt"}
            ],
            "certifications": [
                {"title": "Java Programming Fundamentals", "issuer": "Oracle Academy", "issue_date": "2024-11-20", "credential_url": "https://oracle.com"}
            ],
            "internships": [],
            "backlogs": 1,
            "target_role": "Software Engineer",
            "bio": "Hardworking developer striving to master competitive programming and full-stack software development.",
            "phone": "+91 9876543212",
            "resume_url": "https://drive.google.com/file/d/amit_resume_2026/view",
            "updated_at": datetime.now().isoformat()
        },
        {
            "user_id": user_ids["ananya.verma@college.edu"],
            "email": "ananya.verma@college.edu",
            "full_name": "Ananya Verma",
            "roll_no": "22ECE104",
            "course": "B.Tech",
            "branch": "Electronics",
            "semester": 7,
            "graduation_year": 2026,
            "gender": "Female",
            "dob": "2004-12-05",
            "cgpa": 7.80,
            "aptitude_score": 78.0,
            "technical_score": 72.0,
            "communication_score": 85.0,
            "skills": ["Python", "Linux", "Docker", "AWS", "Bash", "Git", "Critical Thinking", "Collaboration"],
            "programming_languages": ["Python", "Bash", "C"],
            "technical_skills": ["Linux System Administration", "Docker", "Kubernetes", "AWS", "Terraform", "Git"],
            "soft_skills": ["Critical Thinking", "Cross-functional Collaboration", "Public Speaking"],
            "projects": [
                {"title": "Automated CI/CD GitOps Pipeline", "description": "Continuous delivery pipeline using GitHub Actions, Kubernetes, and ArgoCD.", "technologies": ["Docker", "Kubernetes", "GitHub Actions"], "github_url": "https://github.com/ananya/gitops"}
            ],
            "certifications": [
                {"title": "Docker Certified Associate", "issuer": "Mirantis", "issue_date": "2025-04-10", "credential_url": "https://mirantis.com"}
            ],
            "internships": [
                {"company_name": "CloudNine Networks", "role": "DevOps Intern", "duration_months": 2, "description": "Automated infrastructure provisioning using Terraform and configured Prometheus monitoring."}
            ],
            "backlogs": 0,
            "target_role": "Cloud / DevOps Engineer",
            "bio": "Cloud and DevOps enthusiast enthusiastic about resilient cloud infrastructure and developer tooling.",
            "phone": "+91 9876543213",
            "resume_url": "https://drive.google.com/file/d/ananya_resume_2026/view",
            "updated_at": datetime.now().isoformat()
        }
    ]

    student_map = {}
    for st in students_to_seed:
        db.students.update_one({"email": st["email"]}, {"$set": st}, upsert=True)
        found = db.students.find_one({"email": st["email"]})
        student_id = str(found["_id"])
        student_map[st["email"]] = student_id
        
        # Pre-compute predictions
        pred = predictor.predict(found)
        pred["student_id"] = student_id
        pred["student_email"] = st["email"]
        db.predictions.update_one({"student_id": student_id}, {"$set": pred}, upsert=True)

    # 4. Seed Placement Drives
    drives_to_seed = [
        {
            "title": "Google SWE Campus Drive 2026",
            "company_name": "Google",
            "company_id": company_ids.get("Google", ""),
            "recruiter_id": recruiter_ids.get("recruiter@google.com", ""),
            "recruiter_name": "Sundar Raman",
            "recruiter_email": "recruiter@google.com",
            "role": "Software Engineer (L3)",
            "package_lpa": 24.5,
            "min_cgpa": 8.0,
            "required_skills": ["Data Structures", "Algorithms", "Python", "C++", "System Design"],
            "min_aptitude_score": 80.0,
            "max_backlogs": 0,
            "openings": 25,
            "logo_icon": "🌐",
            "eligible_branches": ["Computer Science", "Information Technology", "Electronics"],
            "location": "Bengaluru / Hyderabad",
            "deadline": "2026-10-15",
            "drive_date": "2026-10-25",
            "status": "Active",
            "description": "Google is looking for outstanding software engineers with solid algorithmic foundations and system design acumen.",
            "created_at": datetime.now().isoformat()
        },
        {
            "title": "Microsoft Data & AI Graduate Hire",
            "company_name": "Microsoft",
            "company_id": company_ids.get("Microsoft", ""),
            "recruiter_id": recruiter_ids.get("hiring@microsoft.com", ""),
            "recruiter_name": "Anjali Rao",
            "recruiter_email": "hiring@microsoft.com",
            "role": "Data Scientist / AI Engineer",
            "package_lpa": 22.0,
            "min_cgpa": 8.5,
            "required_skills": ["Python", "Machine Learning", "TensorFlow", "SQL", "Pandas"],
            "min_aptitude_score": 85.0,
            "max_backlogs": 0,
            "openings": 15,
            "logo_icon": "💻",
            "eligible_branches": ["Computer Science", "Information Technology"],
            "location": "Hyderabad",
            "deadline": "2026-10-20",
            "drive_date": "2026-11-01",
            "status": "Active",
            "description": "Join Microsoft AI to build generative intelligence models and enterprise copilot technologies.",
            "created_at": datetime.now().isoformat()
        },
        {
            "title": "Amazon SDE-1 Recruitment Drive",
            "company_name": "Amazon",
            "company_id": company_ids.get("Amazon", ""),
            "recruiter_id": "",
            "recruiter_name": "",
            "recruiter_email": "",
            "role": "Software Development Engineer",
            "package_lpa": 19.8,
            "min_cgpa": 7.5,
            "required_skills": ["Java", "Data Structures", "OOP", "SQL", "Git"],
            "min_aptitude_score": 75.0,
            "max_backlogs": 0,
            "openings": 40,
            "logo_icon": "📦",
            "eligible_branches": ["Computer Science", "Information Technology", "Electronics", "Electrical"],
            "location": "Bengaluru",
            "deadline": "2026-10-30",
            "drive_date": "2026-11-10",
            "status": "Active",
            "description": "Amazon SDE-1 position focusing on distributed high-scale service development and customer obsession.",
            "created_at": datetime.now().isoformat()
        },
        {
            "title": "Goldman Sachs Technology Analyst",
            "company_name": "Goldman Sachs",
            "company_id": company_ids.get("Goldman Sachs", ""),
            "recruiter_id": "",
            "recruiter_name": "",
            "recruiter_email": "",
            "role": "Technology Analyst",
            "package_lpa": 18.0,
            "min_cgpa": 7.0,
            "required_skills": ["Python", "C++", "Java", "SQL", "Algorithms"],
            "min_aptitude_score": 70.0,
            "max_backlogs": 0,
            "openings": 12,
            "logo_icon": "📈",
            "eligible_branches": ["Computer Science", "Information Technology", "Electronics"],
            "location": "Bengaluru",
            "deadline": "2026-11-05",
            "drive_date": "2026-11-15",
            "status": "Upcoming",
            "description": "Fintech engineering role building high-frequency trading platforms and risk analysis engines.",
            "created_at": datetime.now().isoformat()
        },
        {
            "title": "Infosys Specialist Programmer (SP)",
            "company_name": "Infosys",
            "company_id": company_ids.get("Infosys", ""),
            "recruiter_id": "",
            "recruiter_name": "",
            "recruiter_email": "",
            "role": "Specialist Programmer",
            "package_lpa": 9.5,
            "min_cgpa": 6.5,
            "required_skills": ["Java", "Python", "SQL", "Data Structures"],
            "min_aptitude_score": 60.0,
            "max_backlogs": 1,
            "openings": 150,
            "logo_icon": "🏛️",
            "eligible_branches": ["Computer Science", "Information Technology", "Electronics", "Electrical", "Mechanical", "Civil"],
            "location": "Bengaluru / Pune",
            "deadline": "2026-11-15",
            "drive_date": "2026-11-28",
            "status": "Active",
            "description": "Elite developer stream at Infosys for competitive programmers and high-performing engineering students.",
            "created_at": datetime.now().isoformat()
        }
    ]

    drive_ids = {}
    for d in drives_to_seed:
        db.placement_drives.update_one({"title": d["title"]}, {"$set": d}, upsert=True)
        found = db.placement_drives.find_one({"title": d["title"]})
        drive_ids[d["title"]] = str(found["_id"])

    # 5. Seed Applications with Stage Tracking
    applications_to_seed = [
        {
            "student_id": student_map["rahul.sharma@college.edu"],
            "student_name": "Rahul Sharma",
            "student_email": "rahul.sharma@college.edu",
            "roll_no": "22CS101",
            "branch": "Computer Science",
            "cgpa": 8.75,
            "drive_id": drive_ids["Google SWE Campus Drive 2026"],
            "company_name": "Google",
            "role": "Software Engineer (L3)",
            "package_lpa": 24.5,
            "status": "Technical Interview",
            "stage_history": [
                {"stage": "Applied", "timestamp": "2026-09-10T10:00:00", "updated_by": "Student", "remarks": "Application submitted"},
                {"stage": "Shortlisted", "timestamp": "2026-09-15T14:30:00", "updated_by": "Admin", "remarks": "Profile cleared initial academic & project screening"},
                {"stage": "Aptitude Test", "timestamp": "2026-09-20T11:00:00", "updated_by": "Admin", "remarks": "Scored 92/100 in online coding & aptitude challenge"},
                {"stage": "Technical Interview", "timestamp": "2026-09-25T16:00:00", "updated_by": "Admin", "remarks": "Round 1 DSA interview scheduled"}
            ],
            "remarks": "Strong problem solver. Proceeding to Technical Round 2.",
            "applied_at": "2026-09-10T10:00:00",
            "updated_at": "2026-09-25T16:00:00"
        },
        {
            "student_id": student_map["priya.patel@college.edu"],
            "student_name": "Priya Patel",
            "student_email": "priya.patel@college.edu",
            "roll_no": "22CS102",
            "branch": "Computer Science",
            "cgpa": 9.20,
            "drive_id": drive_ids["Microsoft Data & AI Graduate Hire"],
            "company_name": "Microsoft",
            "role": "Data Scientist / AI Engineer",
            "package_lpa": 22.0,
            "status": "Selected",
            "stage_history": [
                {"stage": "Applied", "timestamp": "2026-09-05T09:00:00", "updated_by": "Student", "remarks": "Applied via campus portal"},
                {"stage": "Shortlisted", "timestamp": "2026-09-08T12:00:00", "updated_by": "Admin", "remarks": "High CGPA and top tier research background"},
                {"stage": "Aptitude Test", "timestamp": "2026-09-12T15:00:00", "updated_by": "Admin", "remarks": "Scored 96/100 in ML & Math assessment"},
                {"stage": "Technical Interview", "timestamp": "2026-09-18T10:30:00", "updated_by": "Admin", "remarks": "Deep learning system design interview cleared"},
                {"stage": "HR Interview", "timestamp": "2026-09-22T14:00:00", "updated_by": "Admin", "remarks": "Executive culture fit round cleared"},
                {"stage": "Selected", "timestamp": "2026-09-26T18:00:00", "updated_by": "Admin", "remarks": "Official offer letter released for 22.0 LPA!"}
            ],
            "remarks": "Offer Accepted by Candidate.",
            "applied_at": "2026-09-05T09:00:00",
            "updated_at": "2026-09-26T18:00:00"
        },
        {
            "student_id": student_map["amit.kumar@college.edu"],
            "student_name": "Amit Kumar",
            "student_email": "amit.kumar@college.edu",
            "roll_no": "22IT103",
            "branch": "Information Technology",
            "cgpa": 6.80,
            "drive_id": drive_ids["Infosys Specialist Programmer (SP)"],
            "company_name": "Infosys",
            "role": "Specialist Programmer",
            "package_lpa": 9.5,
            "status": "Aptitude Test",
            "stage_history": [
                {"stage": "Applied", "timestamp": "2026-09-12T11:00:00", "updated_by": "Student", "remarks": "Application submitted"},
                {"stage": "Shortlisted", "timestamp": "2026-09-18T16:00:00", "updated_by": "Admin", "remarks": "Meets 6.5+ CGPA and 1 backlog threshold"},
                {"stage": "Aptitude Test", "timestamp": "2026-09-24T10:00:00", "updated_by": "Admin", "remarks": "Online assessment link dispatched"}
            ],
            "remarks": "Assessment in progress.",
            "applied_at": "2026-09-12T11:00:00",
            "updated_at": "2026-09-24T10:00:00"
        }
    ]

    for app in applications_to_seed:
        db.applications.update_one(
            {"student_id": app["student_id"], "drive_id": app["drive_id"]},
            {"$set": app},
            upsert=True
        )

    logger.info("Successfully completed demo dataset seeding!")
    return {
        "success": True,
        "message": "Demo data successfully seeded into MongoDB!",
        "seeded": True,
        "counts": {
            "users": db.users.count_documents({}),
            "students": db.students.count_documents({}),
            "recruiters": db.recruiters.count_documents({}),
            "companies": db.companies.count_documents({}),
            "placement_drives": db.placement_drives.count_documents({}),
            "applications": db.applications.count_documents({})
        }
    }

if __name__ == "__main__":
    res = run_seed()
    print("Seed result:", res)
