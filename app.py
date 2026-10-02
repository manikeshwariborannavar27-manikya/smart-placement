import os
import json
import logging
from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from bson import ObjectId

# Internal modules
from database import get_db, get_db_status, serialize_doc, is_using_mock_db
from models import (
    StudentProfile, ProjectItem, CertificationItem, InternshipItem,
    CompanyCreate, PlacementDriveCreate, ApplicationStatusUpdate
)
from auth import hash_password, verify_password
from ml_engine import predictor, EligibilityEvaluator, ROLE_SKILL_MAP
from seed_data import run_seed

# Configure Streamlit page
st.set_page_config(
    page_title="Smart Placement Management & Prediction System",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- CREAM + BROWN THEME CSS -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Playfair+Display:wght@600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
    
    :root {
        --bg-cream: #FAF7F2;
        --bg-card: #FFFFFF;
        --bg-card-alt: #F7EFE6;
        --border-beige: #E6D8C8;
        --border-subtle: #EFE4D6;
        --text-dark: #2C1810;
        --text-muted: #5D4037;
        --text-light: #7E6355;
        --brown-primary: #5C381E;
        --brown-hover: #432611;
        --brown-accent: #8B5A2B;
        --brown-light: #EFE4D6;
        --green-soft: #245731;
        --green-bg: #EBF4EC;
        --red-soft: #872820;
        --red-bg: #FAECEA;
    }

    * {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .stApp {
        background-color: var(--bg-cream);
        color: var(--text-dark);
    }
    
    /* Headings */
    h1, h2, h3, h4 {
        color: var(--text-dark) !important;
        font-weight: 700;
    }
    
    p, span, label, div {
        color: var(--text-dark);
    }
    
    /* Primary Cards */
    .cream-card {
        background-color: var(--bg-card);
        border: 1px solid var(--border-beige);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 2px 10px rgba(44, 24, 16, 0.04);
    }
    
    .cream-card-hover {
        background-color: var(--bg-card);
        border: 1px solid var(--border-beige);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 14px;
        box-shadow: 0 2px 8px rgba(44, 24, 16, 0.04);
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    .cream-card-hover:hover {
        border-color: var(--brown-accent);
        box-shadow: 0 6px 16px rgba(92, 56, 30, 0.10);
    }

    /* Hero Banner */
    .hero-banner {
        background: linear-gradient(135deg, #F5EFEB 0%, #EAE0D2 100%);
        border: 1px solid var(--border-beige);
        border-radius: 16px;
        padding: 36px 30px;
        margin-bottom: 24px;
        box-shadow: 0 4px 14px rgba(44, 24, 16, 0.05);
    }
    
    .hero-title {
        font-family: 'Playfair Display', Georgia, serif;
        font-size: 2.4rem;
        font-weight: 700;
        color: #24140D !important;
        line-height: 1.25;
        margin-bottom: 10px;
    }
    
    .hero-subtitle {
        font-size: 1.05rem;
        color: var(--text-muted) !important;
        max-width: 820px;
        line-height: 1.6;
        margin-bottom: 22px;
    }

    /* Metric summary block */
    .stat-box {
        background-color: var(--bg-card);
        border: 1px solid var(--border-beige);
        border-radius: 10px;
        padding: 16px 14px;
        text-align: center;
        box-shadow: 0 2px 6px rgba(44, 24, 16, 0.03);
    }
    .stat-number {
        font-size: 1.85rem;
        font-weight: 800;
        color: var(--brown-primary) !important;
        line-height: 1.1;
    }
    .stat-label {
        font-size: 0.76rem;
        font-weight: 700;
        color: var(--text-light) !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 4px;
    }

    /* Badges */
    .badge-tag {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.78rem;
        font-weight: 700;
    }
    .badge-eligible {
        background-color: var(--green-bg);
        color: var(--green-soft) !important;
        border: 1px solid #C4DFC7;
    }
    .badge-ineligible {
        background-color: var(--red-bg);
        color: var(--red-soft) !important;
        border: 1px solid #ECC6C2;
    }
    .badge-neutral {
        background-color: var(--brown-light);
        color: var(--brown-primary) !important;
        border: 1px solid var(--border-beige);
    }

    /* Skill pill */
    .skill-pill {
        display: inline-block;
        background-color: #F7EFE6;
        color: var(--text-dark) !important;
        border: 1px solid var(--border-beige);
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 5px;
        margin-bottom: 5px;
    }

    /* Step indicator chip */
    .step-chip {
        display: inline-block;
        background-color: #EFE4D6;
        color: var(--text-muted);
        border: 1px solid var(--border-beige);
        padding: 6px 12px;
        border-radius: 6px;
        font-size: 0.78rem;
        font-weight: 700;
        margin-right: 4px;
        margin-bottom: 6px;
    }
    .step-chip-active {
        background-color: var(--brown-primary);
        color: #FFFFFF !important;
        border-color: var(--brown-primary);
    }
    .step-chip-done {
        background-color: var(--green-bg);
        color: var(--green-soft) !important;
        border-color: #C4DFC7;
    }

    /* Sidebar Customization */
    div[data-testid="stSidebar"] {
        background-color: #2C1810;
    }
    div[data-testid="stSidebar"] * {
        color: #FAF7F2 !important;
    }
    div[data-testid="stSidebar"] hr {
        border-color: rgba(250, 247, 242, 0.15) !important;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: var(--brown-primary);
        color: #FFFFFF !important;
        border: none;
        border-radius: 6px;
        font-weight: 600;
        padding: 8px 16px;
        transition: background-color 0.15s ease;
    }
    .stButton > button:hover {
        background-color: var(--brown-hover);
        color: #FFFFFF !important;
    }

    /* Form Fields */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > div {
        background-color: #FFFFFF !important;
        color: var(--text-dark) !important;
        border: 1px solid var(--border-beige) !important;
        border-radius: 6px !important;
    }
</style>
""", unsafe_allow_html=True)

# Database instance
db = get_db()

# Auto-seed initial demo drives & companies if completely empty
if db.placement_drives.count_documents({}) == 0:
    run_seed()

# Helper to compute profile completion %
def compute_profile_completion(st_doc) -> int:
    if not st_doc:
        return 0
    score = 0
    if st_doc.get("full_name") and st_doc.get("email"):
        score += 15
    if st_doc.get("phone") or st_doc.get("roll_no"):
        score += 10
    if st_doc.get("branch") and float(st_doc.get("cgpa", 0.0) or 0.0) > 0:
        score += 20
    skills_len = len(st_doc.get("skills", []) or [])
    if skills_len >= 4:
        score += 20
    elif skills_len >= 1:
        score += 10
    if len(st_doc.get("projects", []) or []) >= 1:
        score += 15
    if len(st_doc.get("internships", []) or []) >= 1 or len(st_doc.get("certifications", []) or []) >= 1:
        score += 10
    if st_doc.get("resume_url") or st_doc.get("linkedin_url"):
        score += 10
    return min(100, score)

# Clean Session State Initialization
if "logged_in_user" not in st.session_state:
    st.session_state["logged_in_user"] = None

if "current_nav" not in st.session_state:
    st.session_state["current_nav"] = "landing"

if "signup_step" not in st.session_state:
    st.session_state["signup_step"] = 1

if "signup_data" not in st.session_state:
    st.session_state["signup_data"] = {
        "skills": [],
        "projects": [],
        "certifications": [],
        "internships": []
    }

if "view_company_id" not in st.session_state:
    st.session_state["view_company_id"] = None

current_user = st.session_state["logged_in_user"]
user_role = current_user["role"] if current_user else "guest"

# Helper for login
def do_login(user_dict):
    st.session_state["logged_in_user"] = user_dict
    st.session_state["current_nav"] = "dashboard"
    st.rerun()

# Helper for logout
def do_logout():
    st.session_state["logged_in_user"] = None
    st.session_state["current_nav"] = "landing"
    st.session_state["signup_step"] = 1
    st.session_state["signup_data"] = {"skills": [], "projects": [], "certifications": [], "internships": []}
    st.rerun()


# ==============================================================================
# SIDEBAR CONTROLS & NAVIGATION
# ==============================================================================

with st.sidebar:
    st.markdown("### 🎓 SmartPlacement")
    st.caption("Cream & Brown Management Portal")

    # DB status
    db_stat = get_db_status()
    if db_stat["is_mock"]:
        st.markdown("""
        <div style="background: rgba(239, 228, 214, 0.12); border-left: 3px solid #D9C3B0; padding: 6px 10px; border-radius: 4px; margin-bottom: 12px;">
            <span style="color: #EFE4D6; font-size: 0.72rem; font-weight: 700;">DATABASE</span><br/>
            <span style="color: #D9C3B0; font-size: 0.7rem;">In-Memory Database Active</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background: rgba(74, 124, 89, 0.2); border-left: 3px solid #95C79E; padding: 6px 10px; border-radius: 4px; margin-bottom: 12px;">
            <span style="color: #B2DFBA; font-size: 0.72rem; font-weight: 700;">DATABASE</span><br/>
            <span style="color: #D9EFE0; font-size: 0.7rem;">Live MongoDB Cluster Connected</span>
        </div>
        """, unsafe_allow_html=True)

    if current_user:
        # Display actual logged in name (NEVER hardcoded)
        st_name_display = current_user.get("full_name") or "Name not provided"
        st.markdown(f"**👤 {st_name_display}**")
        st.caption(f"Role: **{current_user['role'].upper()}** | `{current_user['email']}`")
        
        if st.button("🚪 Sign Out", use_container_width=True):
            do_logout()

        st.markdown("---")

        # STRICT SEPARATION OF MENUS
        if user_role == "student":
            st.markdown("##### 📌 Student Navigation")
            student_menu = st.radio(
                "Go To:",
                [
                    "🏠 Dashboard",
                    "👤 My Profile",
                    "🏢 Placement Opportunities",
                    "📑 My Applications",
                    "🎯 Placement Readiness",
                    "💡 Recommendations & Career Match",
                    "🧠 Aptitude Assessment",
                    "💼 My Internships",
                    "⚙️ Settings"
                ],
                index=0
            )
        elif user_role == "admin":
            st.markdown("##### 📌 Placement Cell Navigation")
            admin_menu = st.radio(
                "Go To:",
                [
                    "📊 Executive Dashboard",
                    "🏢 Placement Drive Management",
                    "👨‍🎓 Student Directory & Portfolios",
                    "📋 Applications & Stage Pipeline",
                    "🏭 Recruiting Partners Directory"
                ],
                index=0
            )
    else:
        st.markdown("##### ⚡ Navigation")
        if st.button("🌐 Landing Page", use_container_width=True):
            st.session_state["current_nav"] = "landing"
            st.rerun()
        if st.button("🔐 Student Login", use_container_width=True):
            st.session_state["current_nav"] = "login"
            st.session_state["login_tab"] = "Student"
            st.rerun()
        if st.button("📝 Student Sign Up", use_container_width=True):
            st.session_state["current_nav"] = "signup"
            st.session_state["signup_step"] = 1
            st.rerun()
        if st.button("🏛️ Admin Login", use_container_width=True):
            st.session_state["current_nav"] = "login"
            st.session_state["login_tab"] = "Admin"
            st.rerun()

        st.markdown("---")
        st.markdown("##### ⚡ Quick Admin Access")
        if st.button("🏛️ Demo Placement Officer", use_container_width=True):
            u_admin = db.users.find_one({"role": "admin"})
            if not u_admin:
                run_seed()
                u_admin = db.users.find_one({"role": "admin"})
            if u_admin:
                do_login({
                    "id": str(u_admin["_id"]),
                    "email": u_admin["email"],
                    "full_name": u_admin.get("full_name") or "Placement Officer",
                    "role": "admin",
                    "student_id": None
                })


# ==============================================================================
# GUEST VIEW 1: LANDING PAGE
# ==============================================================================

if not current_user and st.session_state.get("current_nav") == "landing":
    
    # Top Navigation Bar Header
    st.markdown("""
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background-color: #FFFFFF; border: 1px solid #E6D8C8; border-radius: 10px; margin-bottom: 20px;">
        <div style="font-size: 1.25rem; font-weight: 800; color: #2C1810;">🎓 SmartPlacement</div>
        <div style="font-size: 0.9rem; color: #5D4037; font-weight: 600;">
            Home &nbsp;•&nbsp; How It Works &nbsp;•&nbsp; Companies &nbsp;•&nbsp; Features
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Hero Section
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">
            Smart Placement Management & Prediction System
        </div>
        <div class="hero-subtitle">
            Understand your placement readiness, discover suitable opportunities, and build the skills you need for your career. A warm, streamlined platform connecting student potential with company requirements.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Hero CTA Buttons
    c_btn1, c_btn2, c_btn3, _ = st.columns([1.4, 1.4, 1.4, 3.8])
    with c_btn1:
        if st.button("🚀 Get Started", use_container_width=True):
            st.session_state["current_nav"] = "signup"
            st.session_state["signup_step"] = 1
            st.rerun()
    with c_btn2:
        if st.button("🔐 Student Login", use_container_width=True):
            st.session_state["current_nav"] = "login"
            st.session_state["login_tab"] = "Student"
            st.rerun()
    with c_btn3:
        if st.button("🏛️ Admin Login", use_container_width=True):
            st.session_state["current_nav"] = "login"
            st.session_state["login_tab"] = "Admin"
            st.rerun()

    st.markdown("<br/>", unsafe_allow_html=True)

    # Database-Driven Statistics (0 if empty)
    st.markdown("### 📊 Live Campus Placement Statistics")
    
    cnt_students = db.students.count_documents({})
    cnt_companies = db.companies.count_documents({})
    cnt_drives = db.placement_drives.count_documents({"status": "Active"})
    cnt_placed = db.applications.count_documents({"status": "Selected"})

    n1, n2, n3, n4 = st.columns(4)
    with n1:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{cnt_students}</div>
            <div class="stat-label">Students</div>
        </div>
        """, unsafe_allow_html=True)
    with n2:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{cnt_companies}</div>
            <div class="stat-label">Companies</div>
        </div>
        """, unsafe_allow_html=True)
    with n3:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{cnt_drives}</div>
            <div class="stat-label">Placement Drives</div>
        </div>
        """, unsafe_allow_html=True)
    with n4:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number" style="color: #245731 !important;">{cnt_placed}</div>
            <div class="stat-label">Students Placed</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br/><hr style='border-color: #E6D8C8;'/><br/>", unsafe_allow_html=True)

    # How It Works
    st.markdown("### ⚡ How It Works")
    
    hw1, hw2, hw3 = st.columns(3)
    with hw1:
        st.markdown("""
        <div class="cream-card">
            <h4 style="color: #5C381E !important; margin-top: 0;">1. Create Your Profile</h4>
            <p style="font-size: 0.88rem; color: #5D4037; line-height: 1.5;">Enter your academic details, skills, LinkedIn profile, projects, and assessment scores into MongoDB.</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div class="cream-card">
            <h4 style="color: #5C381E !important; margin-top: 0;">4. Analyze Your Readiness</h4>
            <p style="font-size: 0.88rem; color: #5D4037; line-height: 1.5;">Machine learning calculates your placement readiness score, strengths, and competency breakdown.</p>
        </div>
        """, unsafe_allow_html=True)
    with hw2:
        st.markdown("""
        <div class="cream-card">
            <h4 style="color: #5C381E !important; margin-top: 0;">2. Check Eligibility</h4>
            <p style="font-size: 0.88rem; color: #5D4037; line-height: 1.5;">Instant 5-factor evaluation against company cutoffs (CGPA, aptitude, backlogs, branch, and required skills).</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div class="cream-card">
            <h4 style="color: #5C381E !important; margin-top: 0;">5. Improve Your Skills</h4>
            <p style="font-size: 0.88rem; color: #5D4037; line-height: 1.5;">Receive personalized skill gap recommendations and projects targeted towards your dream career role.</p>
        </div>
        """, unsafe_allow_html=True)
    with hw3:
        st.markdown("""
        <div class="cream-card">
            <h4 style="color: #5C381E !important; margin-top: 0;">3. Discover Placement Opportunities</h4>
            <p style="font-size: 0.88rem; color: #5D4037; line-height: 1.5;">Explore active company recruitment drives and apply with verified eligibility.</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div class="cream-card">
            <h4 style="color: #5C381E !important; margin-top: 0;">6. Track Your Applications</h4>
            <p style="font-size: 0.88rem; color: #5D4037; line-height: 1.5;">Live stage pipeline tracking from Applied → Shortlisted → Technical Rounds → Offer Release.</p>
        </div>
        """, unsafe_allow_html=True)

    # Footer
    st.markdown("""
    <br/><br/>
    <div style="text-align: center; color: #7E6355; font-size: 0.85rem; padding: 20px; border-top: 1px solid #E6D8C8;">
        Smart Placement Management & Prediction System • Cream & Brown Edition • Real Student Data Architecture
    </div>
    """, unsafe_allow_html=True)


# ==============================================================================
# GUEST VIEW 2: LOGIN PAGE
# ==============================================================================

elif not current_user and st.session_state.get("current_nav") == "login":
    
    st.markdown("""
    <div style="max-width: 480px; margin: 25px auto 10px auto; text-align: center;">
        <h2 style="color: #2C1810; margin-bottom: 4px;">🔐 Portal Sign In</h2>
        <p style="color: #5D4037; font-size: 0.92rem;">Select your role to access your dedicated placement tools.</p>
    </div>
    """, unsafe_allow_html=True)

    col_lg_l, col_lg_m, col_lg_r = st.columns([1, 2, 1])
    with col_lg_m:
        tab_st_login, tab_ad_login = st.tabs(["👨‍🎓 Student Sign In", "🏛️ Admin / Officer Sign In"])

        with tab_st_login:
            st.markdown("<br/>", unsafe_allow_html=True)
            with st.form("student_login_form"):
                st_em = st.text_input("Student Email Address", placeholder="Enter your registered email")
                st_pw = st.text_input("Password", type="password", placeholder="Enter your password")
                
                c_sb1, c_sb2 = st.columns(2)
                with c_sb1:
                    btn_st_login = st.form_submit_button("Sign In as Student", use_container_width=True)
                with c_sb2:
                    if st.form_submit_button("Forgot Password?", use_container_width=True):
                        st.info("Password reset instructions sent to your email.")

                if btn_st_login:
                    if not st_em or not st_pw:
                        st.error("Please provide both email and password.")
                    else:
                        u = db.users.find_one({"email": st_em.lower().strip()})
                        if u and verify_password(st_pw, u.get("password_hash", "")):
                            if u.get("role") != "student":
                                st.error("This is an Admin account. Please use the Admin tab.")
                            else:
                                s_prof = db.students.find_one({"email": u["email"]})
                                do_login({
                                    "id": str(u["_id"]),
                                    "email": u["email"],
                                    "full_name": u.get("full_name") or "Name not provided",
                                    "role": "student",
                                    "student_id": str(s_prof["_id"]) if s_prof else None
                                })
                        else:
                            st.error("Invalid student email or password.")

            st.markdown("<div style='text-align: center; margin: 12px 0 6px 0; color: #5D4037;'>New student?</div>", unsafe_allow_html=True)
            if st.button("📝 Register New Student Profile", use_container_width=True):
                st.session_state["current_nav"] = "signup"
                st.session_state["signup_step"] = 1
                st.rerun()

        with tab_ad_login:
            st.markdown("<br/>", unsafe_allow_html=True)
            with st.form("admin_login_form"):
                ad_em = st.text_input("Placement Officer Email", placeholder="e.g. admin@placement.edu")
                ad_pw = st.text_input("Admin Password", type="password", placeholder="Enter admin password")
                btn_ad_login = st.form_submit_button("Sign In as Placement Officer", use_container_width=True)

                if btn_ad_login:
                    if not ad_em or not ad_pw:
                        st.error("Please enter admin credentials.")
                    else:
                        u = db.users.find_one({"email": ad_em.lower().strip()})
                        if u and verify_password(ad_pw, u.get("password_hash", "")):
                            if u.get("role") != "admin":
                                st.error("This account does not have administrative privileges.")
                            else:
                                do_login({
                                    "id": str(u["_id"]),
                                    "email": u["email"],
                                    "full_name": u.get("full_name") or "Placement Officer",
                                    "role": "admin",
                                    "student_id": None
                                })
                        else:
                            st.error("Invalid admin credentials.")


# ==============================================================================
# GUEST VIEW 3: 8-STEP STUDENT SIGN UP WIZARD (REAL STUDENT DATA ONLY)
# ==============================================================================

elif not current_user and st.session_state.get("current_nav") == "signup":
    
    signup_step = st.session_state.get("signup_step", 1)
    s_data = st.session_state.get("signup_data", {})

    st.markdown("""
    <div style="max-width: 860px; margin: 15px auto 10px auto;">
        <h2 style="color: #2C1810; margin-bottom: 2px;">📝 Student Registration Wizard</h2>
        <p style="color: #5D4037; font-size: 0.92rem;">Enter your own details. Real data will be saved directly into MongoDB and analyzed by the ML prediction engine.</p>
    </div>
    """, unsafe_allow_html=True)

    # 8 Steps Chip Indicator
    step_titles = [
        "1. Personal Info", "2. Academic Info", "3. Technical Skills", 
        "4. Projects", "5. Certifications", "6. Internships", 
        "7. Aptitude & Scores", "8. Review Profile"
    ]
    
    chip_html = "<div style='margin-bottom: 18px;'>"
    for i, stitle in enumerate(step_titles, start=1):
        if i == signup_step:
            chip_html += f"<span class='step-chip step-chip-active'>{stitle}</span>"
        elif i < signup_step:
            chip_html += f"<span class='step-chip step-chip-done'>✓ {stitle}</span>"
        else:
            chip_html += f"<span class='step-chip'>{stitle}</span>"
    chip_html += "</div>"
    st.markdown(chip_html, unsafe_allow_html=True)

    col_w_l, col_w_m, col_w_r = st.columns([1, 4, 1])
    with col_w_m:
        
        # ---------------- STEP 1: PERSONAL INFORMATION ----------------
        if signup_step == 1:
            st.markdown("#### 👤 Step 1 — Personal Information")
            with st.form("step1_personal"):
                p_name = st.text_input("Full Name *", value=s_data.get("full_name", ""), placeholder="Enter your full name")
                p_email = st.text_input("Email Address *", value=s_data.get("email", ""), placeholder="Enter your personal/college email")
                p_pw = st.text_input("Create Password *", type="password", value=s_data.get("password", ""), placeholder="Create a secure password")
                
                c_p1, c_p2 = st.columns(2)
                with c_p1:
                    p_phone = st.text_input("Phone Number", value=s_data.get("phone", ""), placeholder="+91 9876543210")
                    p_dob = st.text_input("Date of Birth", value=s_data.get("dob", "2004-05-15"), placeholder="YYYY-MM-DD")
                with c_p2:
                    p_gender = st.selectbox("Gender", ["Female", "Male", "Other", "Prefer not to say"], index=0)
                    p_linkedin = st.text_input("LinkedIn Profile URL", value=s_data.get("linkedin_url", ""), placeholder="https://www.linkedin.com/in/yourprofile")

                if st.form_submit_button("Next: Academic Details →", use_container_width=True):
                    if not p_name.strip() or not p_email.strip() or not p_pw:
                        st.error("Full Name, Email, and Password are required.")
                    elif db.users.find_one({"email": p_email.lower().strip()}):
                        st.error("A user with this email address already exists.")
                    else:
                        s_data.update({
                            "full_name": p_name.strip(),
                            "email": p_email.lower().strip(),
                            "password": p_pw,
                            "phone": p_phone.strip(),
                            "dob": p_dob.strip(),
                            "gender": p_gender,
                            "linkedin_url": p_linkedin.strip()
                        })
                        st.session_state["signup_data"] = s_data
                        st.session_state["signup_step"] = 2
                        st.rerun()

        # ---------------- STEP 2: ACADEMIC INFORMATION ----------------
        elif signup_step == 2:
            st.markdown("#### 🎓 Step 2 — Academic Information")
            with st.form("step2_academic"):
                a_college = st.text_input("College / University Name", value=s_data.get("college_name", ""))
                
                c_a1, c_a2 = st.columns(2)
                with c_a1:
                    a_course = st.selectbox("Course / Program", ["B.Tech", "B.E", "M.Tech", "MCA", "B.Sc CS", "BCA"], index=0)
                    a_dept = st.selectbox("Department / Branch", ["Computer Science", "Information Technology", "Electronics", "Electrical", "Mechanical", "Civil"], index=0)
                    a_year = st.selectbox("Current Year", [1, 2, 3, 4], index=3)
                    a_sem = st.selectbox("Current Semester", [1, 2, 3, 4, 5, 6, 7, 8], index=6)
                with c_a2:
                    a_cgpa = st.number_input("Cumulative GPA (CGPA 0.0 - 10.0) *", min_value=0.0, max_value=10.0, value=float(s_data.get("cgpa", 7.50)), step=0.01)
                    a_10th = st.number_input("10th Standard Percentage (%)", min_value=0.0, max_value=100.0, value=float(s_data.get("tenth_percentage", 85.0)), step=0.1)
                    a_12th = st.number_input("12th / Diploma Percentage (%)", min_value=0.0, max_value=100.0, value=float(s_data.get("twelfth_percentage", 82.0)), step=0.1)
                    a_backlogs = st.number_input("Number of Active Backlogs", min_value=0, max_value=10, value=int(s_data.get("backlogs", 0)))

                c_b, c_n = st.columns(2)
                with c_b:
                    if st.form_submit_button("← Back"):
                        st.session_state["signup_step"] = 1
                        st.rerun()
                with c_n:
                    if st.form_submit_button("Next: Technical Skills →"):
                        s_data.update({
                            "college_name": a_college,
                            "course": a_course,
                            "branch": a_dept,
                            "current_year": a_year,
                            "semester": a_sem,
                            "cgpa": a_cgpa,
                            "tenth_percentage": a_10th,
                            "twelfth_percentage": a_12th,
                            "backlogs": a_backlogs
                        })
                        st.session_state["signup_data"] = s_data
                        st.session_state["signup_step"] = 3
                        st.rerun()

        # ---------------- STEP 3: TECHNICAL SKILLS ----------------
        elif signup_step == 3:
            st.markdown("#### ⚡ Step 3 — Technical Skills")
            st.caption("Select from suggested skills and add your own custom skills.")
            
            catalog = ["Python", "Java", "C", "C++", "SQL", "HTML", "CSS", "JavaScript", "React", "Node.js", "FastAPI", "MongoDB", "Power BI", "Excel", "Docker", "Git", "Machine Learning"]
            curr_skills = s_data.get("skills", [])

            with st.form("step3_skills"):
                sel_skills = st.multiselect("Select Skills", catalog, default=[s for s in curr_skills if s in catalog])
                custom_skills_input = st.text_input("Add Custom Skills (comma-separated)", placeholder="e.g. Flutter, PyTorch, GraphQL, Tableau")
                
                c_b, c_n = st.columns(2)
                with c_b:
                    if st.form_submit_button("← Back"):
                        st.session_state["signup_step"] = 2
                        st.rerun()
                with c_n:
                    if st.form_submit_button("Next: Projects →"):
                        custom_skills = [c.strip() for c in custom_skills_input.split(",") if c.strip()]
                        s_data["skills"] = list(set(sel_skills + custom_skills))
                        st.session_state["signup_data"] = s_data
                        st.session_state["signup_step"] = 4
                        st.rerun()

        # ---------------- STEP 4: PROJECTS ----------------
        elif signup_step == 4:
            st.markdown("#### 📁 Step 4 — Projects")
            st.caption("Add your academic or portfolio projects (Optional).")
            
            proj_list = s_data.get("projects", [])
            if proj_list:
                st.markdown("**Added Projects:**")
                for p in proj_list:
                    st.markdown(f"• **{p['title']}** ({', '.join(p.get('technologies', []))}) — [GitHub]({p.get('github_url', '#')})")

            with st.form("step4_add_project"):
                p_title = st.text_input("Project Name", placeholder="e.g. Smart Placement Prediction System")
                p_desc = st.text_area("Description", placeholder="Describe project features and your contribution...")
                p_tech = st.text_input("Technologies Used (comma-separated)", placeholder="e.g. Python, FastAPI, Streamlit, MongoDB")
                p_gh = st.text_input("GitHub Link", placeholder="https://github.com/...")
                p_live = st.text_input("Live Project Link", placeholder="https://...")
                
                if st.form_submit_button("➕ Add Project"):
                    if p_title.strip():
                        proj_list.append({
                            "title": p_title.strip(),
                            "description": p_desc.strip(),
                            "technologies": [t.strip() for t in p_tech.split(",") if t.strip()],
                            "github_url": p_gh.strip(),
                            "live_url": p_live.strip()
                        })
                        s_data["projects"] = proj_list
                        st.session_state["signup_data"] = s_data
                        st.success(f"Added project '{p_title}'!")
                        st.rerun()

            c_b, c_n = st.columns(2)
            with c_b:
                if st.button("← Back"):
                    st.session_state["signup_step"] = 3
                    st.rerun()
            with c_n:
                if st.button("Next: Certifications →"):
                    st.session_state["signup_step"] = 5
                    st.rerun()

        # ---------------- STEP 5: CERTIFICATIONS ----------------
        elif signup_step == 5:
            st.markdown("#### 📜 Step 5 — Certifications")
            st.caption("Add your professional or online certificates (Optional).")
            
            cert_list = s_data.get("certifications", [])
            if cert_list:
                st.markdown("**Added Certifications:**")
                for c in cert_list:
                    st.markdown(f"• **{c['title']}** (Issuer: {c['issuer']})")

            with st.form("step5_add_cert"):
                c_title = st.text_input("Certification Name", placeholder="e.g. AWS Certified Cloud Practitioner")
                c_org = st.text_input("Organization", placeholder="e.g. Amazon Web Services / Coursera")
                c_date = st.text_input("Date", value=datetime.now().strftime("%Y-%m-%d"))
                c_link = st.text_input("Certificate Verification Link", placeholder="https://...")
                
                if st.form_submit_button("➕ Add Certification"):
                    if c_title.strip():
                        cert_list.append({
                            "title": c_title.strip(),
                            "issuer": c_org.strip(),
                            "issue_date": c_date.strip(),
                            "credential_url": c_link.strip()
                        })
                        s_data["certifications"] = cert_list
                        st.session_state["signup_data"] = s_data
                        st.success(f"Added certification '{c_title}'!")
                        st.rerun()

            c_b, c_n = st.columns(2)
            with c_b:
                if st.button("← Back"):
                    st.session_state["signup_step"] = 4
                    st.rerun()
            with c_n:
                if st.button("Next: Internships →"):
                    st.session_state["signup_step"] = 6
                    st.rerun()

        # ---------------- STEP 6: INTERNSHIPS ----------------
        elif signup_step == 6:
            st.markdown("#### 🏢 Step 6 — Internships")
            st.caption("Add verified internships. If you don't have an internship, simply click 'I don't have an internship' or Next.")
            
            intern_list = s_data.get("internships", [])
            if intern_list:
                st.markdown("**Added Internships:**")
                for it in intern_list:
                    st.markdown(f"• **{it['company_name']}** — {it['role']} ({it['duration_months']} mo)")
            else:
                st.info("ℹ️ **I don't have an internship yet** (You can proceed directly).")

            with st.form("step6_add_intern"):
                it_comp = st.text_input("Company", placeholder="e.g. TechSprint Labs")
                it_role = st.text_input("Role", placeholder="e.g. Software Engineering Intern")
                it_dur = st.number_input("Duration (Months)", min_value=1, max_value=24, value=3)
                it_tech = st.text_input("Technologies / Skills Used", placeholder="e.g. Python, SQL, Git")
                it_desc = st.text_area("Description", placeholder="Describe your responsibilities and achievements...")
                
                if st.form_submit_button("➕ Add Internship"):
                    if it_comp.strip():
                        intern_list.append({
                            "company_name": it_comp.strip(),
                            "role": it_role.strip(),
                            "duration_months": it_dur,
                            "technologies": [t.strip() for t in it_tech.split(",") if t.strip()],
                            "description": it_desc.strip()
                        })
                        s_data["internships"] = intern_list
                        st.session_state["signup_data"] = s_data
                        st.success(f"Added internship at {it_comp}!")
                        st.rerun()

            c_b, c_n = st.columns(2)
            with c_b:
                if st.button("← Back"):
                    st.session_state["signup_step"] = 5
                    st.rerun()
            with c_n:
                if st.button("Next: Aptitude Assessment →"):
                    st.session_state["signup_step"] = 7
                    st.rerun()

        # ---------------- STEP 7: APTITUDE ASSESSMENT & SCORES ----------------
        elif signup_step == 7:
            st.markdown("#### 🧠 Step 7 — Aptitude Assessment Performance")
            st.caption("Enter or calibrate your scores for Quantitative, Logical, and Verbal ability.")
            
            with st.form("step7_aptitude"):
                c_ap1, c_ap2, c_ap3 = st.columns(3)
                with c_ap1:
                    sc_quant = st.slider("Quantitative Aptitude", 0.0, 100.0, float(s_data.get("quant_score", 75.0)), 1.0)
                with c_ap2:
                    sc_log = st.slider("Logical Reasoning", 0.0, 100.0, float(s_data.get("logical_score", 80.0)), 1.0)
                with c_ap3:
                    sc_verb = st.slider("Verbal Ability", 0.0, 100.0, float(s_data.get("verbal_score", 75.0)), 1.0)

                overall_apt = round((sc_quant + sc_log + sc_verb) / 3.0, 1)
                st.markdown(f"**Calculated Overall Aptitude Score:** <span style='font-size: 1.15rem; font-weight: 800; color: #5C381E;'>{overall_apt}/100</span>", unsafe_allow_html=True)

                st.markdown("---")
                c_cm1, c_cm2 = st.columns(2)
                with c_cm1:
                    sc_comm = st.slider("Communication / Soft Skills (0-100)", 0.0, 100.0, float(s_data.get("communication_score", 75.0)), 1.0)
                with c_cm2:
                    sc_tech = st.slider("Technical Coding Assessment (0-100)", 0.0, 100.0, float(s_data.get("technical_score", 75.0)), 1.0)

                c_tg1, c_tg2 = st.columns(2)
                with c_tg1:
                    target_role_pick = st.selectbox("Target Career Role", list(ROLE_SKILL_MAP.keys()), index=0)
                with c_tg2:
                    gh_link = st.text_input("GitHub Profile URL", value=s_data.get("github_url", ""), placeholder="https://github.com/yourusername")

                c_b, c_n = st.columns(2)
                with c_b:
                    if st.form_submit_button("← Back"):
                        st.session_state["signup_step"] = 6
                        st.rerun()
                with c_n:
                    if st.form_submit_button("Next: Review Profile →"):
                        s_data.update({
                            "quant_score": sc_quant,
                            "logical_score": sc_log,
                            "verbal_score": sc_verb,
                            "aptitude_score": overall_apt,
                            "communication_score": sc_comm,
                            "technical_score": sc_tech,
                            "target_role": target_role_pick,
                            "github_url": gh_link.strip()
                        })
                        st.session_state["signup_data"] = s_data
                        st.session_state["signup_step"] = 8
                        st.rerun()

        # ---------------- STEP 8: REVIEW & SUBMIT ----------------
        elif signup_step == 8:
            st.markdown("#### ✅ Step 8 — Review Profile & Complete Registration")
            
            st.markdown(f"""
            <div class="cream-card">
                <h3 style="margin-top: 0; color: #2C1810;">{s_data.get('full_name') or 'Name not provided'}</h3>
                <div style="color: #5C381E; font-weight: 700;">{s_data.get('email')} | {s_data.get('phone')}</div>
                <hr style="border-color: #E6D8C8; margin: 12px 0;">
                <div style="font-size: 0.9rem; color: #5D4037; line-height: 1.6;">
                    <b>College:</b> {s_data.get('college_name') or 'N/A'}<br/>
                    <b>Program:</b> {s_data.get('course')} in {s_data.get('branch')} (Sem {s_data.get('semester')})<br/>
                    <b>Academic Score:</b> CGPA <b>{s_data.get('cgpa'):.2f}</b> | Backlogs: <b>{s_data.get('backlogs')}</b><br/>
                    <b>LinkedIn:</b> {s_data.get('linkedin_url') or 'Not provided'}<br/>
                    <b>Target Role:</b> {s_data.get('target_role')}<br/>
                    <b>Skills ({len(s_data.get('skills', []))}):</b> {', '.join(s_data.get('skills', [])) or 'None'}<br/>
                    <b>Projects:</b> {len(s_data.get('projects', []))} | <b>Certifications:</b> {len(s_data.get('certifications', []))} | <b>Internships:</b> {len(s_data.get('internships', []))}
                </div>
            </div>
            """, unsafe_allow_html=True)

            c_b, c_sub = st.columns([1, 2])
            with c_b:
                if st.button("← Back to Edit"):
                    st.session_state["signup_step"] = 7
                    st.rerun()
            with c_sub:
                if st.button("🚀 Create My Profile", type="primary", use_container_width=True):
                    now_iso = datetime.now().isoformat()
                    actual_name = s_data["full_name"].strip()
                    
                    # 1. Create User
                    user_doc = {
                        "email": s_data["email"],
                        "password_hash": hash_password(s_data["password"]),
                        "full_name": actual_name,
                        "role": "student",
                        "created_at": now_iso
                    }
                    u_res = db.users.insert_one(user_doc)
                    user_id = str(u_res.inserted_id)

                    # 2. Create Student Profile in MongoDB
                    st_doc = {
                        "user_id": user_id,
                        "email": s_data["email"],
                        "full_name": actual_name,
                        "roll_no": s_data.get("roll_no", ""),
                        "college_name": s_data.get("college_name", ""),
                        "course": s_data.get("course", "B.Tech"),
                        "branch": s_data.get("branch", "Computer Science"),
                        "current_year": s_data.get("current_year", 4),
                        "semester": s_data.get("semester", 7),
                        "graduation_year": 2026,
                        "gender": s_data.get("gender", "Not Specified"),
                        "dob": s_data.get("dob", ""),
                        "linkedin_url": s_data.get("linkedin_url", ""),
                        "github_url": s_data.get("github_url", ""),
                        "cgpa": float(s_data.get("cgpa", 0.0)),
                        "tenth_percentage": float(s_data.get("tenth_percentage", 0.0)),
                        "twelfth_percentage": float(s_data.get("twelfth_percentage", 0.0)),
                        "quant_score": float(s_data.get("quant_score", 70.0)),
                        "logical_score": float(s_data.get("logical_score", 70.0)),
                        "verbal_score": float(s_data.get("verbal_score", 70.0)),
                        "aptitude_score": float(s_data.get("aptitude_score", 70.0)),
                        "technical_score": float(s_data.get("technical_score", 75.0)),
                        "communication_score": float(s_data.get("communication_score", 70.0)),
                        "backlogs": int(s_data.get("backlogs", 0)),
                        "target_role": s_data.get("target_role", "Software Engineer"),
                        "skills": s_data.get("skills", []),
                        "projects": s_data.get("projects", []),
                        "certifications": s_data.get("certifications", []),
                        "internships": s_data.get("internships", []),
                        "resume_url": s_data.get("resume_url", ""),
                        "bio": s_data.get("bio", ""),
                        "phone": s_data.get("phone", ""),
                        "is_demo": False,
                        "updated_at": now_iso
                    }
                    s_res = db.students.insert_one(st_doc)
                    student_id = str(s_res.inserted_id)

                    # 3. Compute initial ML prediction
                    pred_res = predictor.predict(st_doc)
                    pred_res["student_id"] = student_id
                    pred_res["student_email"] = s_data["email"]
                    db.predictions.update_one({"student_id": student_id}, {"$set": pred_res}, upsert=True)

                    st.success("🎉 Profile created successfully!")
                    do_login({
                        "id": user_id,
                        "email": s_data["email"],
                        "full_name": actual_name,
                        "role": "student",
                        "student_id": student_id
                    })


# ==============================================================================
# LOGGED IN VIEW: STUDENT PORTAL (REAL DATA ONLY)
# ==============================================================================

elif current_user and user_role == "student":
    
    st_email = current_user["email"]
    student = db.students.find_one({"email": st_email})
    
    # Use real name from MongoDB (fallback to 'Name not provided')
    actual_student_name = student.get("full_name") if student and student.get("full_name") else (current_user.get("full_name") or "Name not provided")
    student_id = str(student["_id"]) if student else ""
    
    if student:
        pred = predictor.predict(student)
        completion_pct = compute_profile_completion(student)
    else:
        pred = {"readiness_score": 0.0, "readiness_category": "Needs Improvement", "estimated_package_range": "N/A", "strengths": [], "weaknesses": [], "recommendations": [], "radar_scores": {}, "disclaimer": ""}
        completion_pct = 0

    # ---------------- 1. DASHBOARD (TOP HORIZONTAL LAYOUT) ----------------
    if student_menu == "🏠 Dashboard":
        
        # Welcome Header with EXACT student name
        st.markdown(f"""
        <div class="cream-card" style="background: linear-gradient(135deg, #F5EFEB 0%, #EAE0D2 100%); padding: 22px; border-radius: 14px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h1 style="margin: 0; font-size: 1.8rem; color: #2C1810 !important;">Welcome, {actual_student_name}</h1>
                    <p style="color: #5D4037; margin: 4px 0 0 0; font-size: 0.92rem;">
                        {student.get('course', 'B.Tech') if student else ''} in {student.get('branch', 'Engineering') if student else ''} (Sem {student.get('semester', 7) if student else ''}) | Target Role: <span style="color: #5C381E; font-weight: 800;">{student.get('target_role', 'Software Engineer') if student else ''}</span>
                    </p>
                </div>
                <div>
                    <span class="badge-tag badge-neutral">Placement Portal Active</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # TOP HORIZONTAL SUMMARY CARDS
        all_drives = list(db.placement_drives.find({"status": "Active"}))
        eligible_drives = [d for d in all_drives if student and EligibilityEvaluator.evaluate(student, d)["is_eligible"]]
        my_apps = list(db.applications.find({"student_id": student_id})) if student_id else []
        internships_count = len(student.get("internships", [])) if student else 0

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-number">{pred['readiness_score']}%</div>
                <div class="stat-label">Readiness</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-number">{len(eligible_drives)} Companies</div>
                <div class="stat-label">Eligible</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-number">{len(my_apps)}</div>
                <div class="stat-label">Applications</div>
            </div>
            """, unsafe_allow_html=True)
        with c4:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-number">{internships_count}</div>
                <div class="stat-label">Internships</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br/>", unsafe_allow_html=True)

        # PLACEMENT READINESS & STRENGTHS / WEAKNESSES
        col_rd_l, col_rd_r = st.columns([1, 1.6])
        with col_rd_l:
            st.markdown("### 🎯 Placement Readiness")
            st.markdown(f"""
            <div class="cream-card" style="text-align: center;">
                <div style="font-size: 2.8rem; font-weight: 800; color: #5C381E;">{pred['readiness_score']} / 100</div>
                <div class="badge-tag badge-neutral" style="font-size: 0.85rem; margin-top: 4px;">
                    {pred['readiness_category']}
                </div>
                <div style="font-size: 0.85rem; color: #5D4037; margin-top: 10px;">Estimated Campus Package: <b style="color: #245731;">{pred['estimated_package_range']}</b></div>
            </div>
            """, unsafe_allow_html=True)

        with col_rd_r:
            st.markdown("### 🔍 Strengths & Areas to Improve")
            c_str, c_imp = st.columns(2)
            with c_str:
                st.markdown("**Strengths:**")
                for s in pred["strengths"][:3]:
                    st.markdown(f"<div style='background-color: #EBF4EC; border: 1px solid #C4DFC7; border-radius: 6px; padding: 6px 10px; margin-bottom: 6px; font-size: 0.82rem; color: #245731;'>✓ {s}</div>", unsafe_allow_html=True)
            with c_imp:
                st.markdown("**Improve:**")
                for w in pred["weaknesses"][:3]:
                    st.markdown(f"<div style='background-color: #FAECEA; border: 1px solid #ECC6C2; border-radius: 6px; padding: 6px 10px; margin-bottom: 6px; font-size: 0.82rem; color: #872820;'>✕ {w}</div>", unsafe_allow_html=True)

        st.markdown("<br/>", unsafe_allow_html=True)

        # RECOMMENDED OPPORTUNITIES
        st.markdown("### 💼 Recommended Opportunities")
        if not eligible_drives:
            st.info("No matching drives eligible at this moment. Update your skills or explore the Company Directory.")
        else:
            for drive in eligible_drives[:3]:
                d_id = str(drive["_id"])
                st.markdown(f"""
                <div class="cream-card-hover">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <span style="font-size: 1.2rem;">{drive.get('logo_icon', '🏢')}</span>
                            <span style="font-size: 1.15rem; font-weight: 700; color: #2C1810; margin-left: 6px;">{drive.get('company_name')}</span>
                            <div style="color: #5C381E; font-weight: 700; font-size: 0.95rem; margin-top: 2px;">{drive.get('role')}</div>
                            <div style="color: #5D4037; font-size: 0.82rem; margin-top: 2px;">📍 {drive.get('location', 'Onsite')} | 📅 Deadline: {drive.get('deadline', 'Open')}</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 1.35rem; font-weight: 800; color: #245731;">{drive.get('package_lpa', 0.0):.1f} LPA</div>
                            <span class='badge-tag badge-eligible'>✓ Eligible</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<br/>", unsafe_allow_html=True)

        # RECENT APPLICATIONS & UPCOMING DRIVES
        col_bt1, col_bt2 = st.columns([1.2, 1])
        with col_bt1:
            st.markdown("### 📑 Recent Applications")
            if not my_apps:
                st.info("No applications submitted yet.")
            else:
                table_apps = []
                for a in my_apps[:4]:
                    table_apps.append({
                        "Company": a.get("company_name"),
                        "Role": a.get("role"),
                        "Package": f"{a.get('package_lpa', 0.0):.1f} LPA",
                        "Status": a.get("status"),
                        "Applied Date": a.get("applied_at", "")[:10]
                    })
                st.dataframe(pd.DataFrame(table_apps), use_container_width=True)

        with col_bt2:
            st.markdown("### 🏢 Upcoming Placement Drives")
            for dr in all_drives[:3]:
                st.markdown(f"• **{dr.get('company_name')}** — {dr.get('role')} ({dr.get('package_lpa', 0.0):.1f} LPA)")

    # ---------------- 2. STUDENT PROFILE UI ----------------
    elif student_menu == "👤 My Profile":
        st.markdown(f"""
        <div class="cream-card">
            <h2 style="margin:0; color: #2C1810;">👤 Student Profile — {actual_student_name}</h2>
            <p style="color: #5D4037; font-size: 0.92rem; margin-top: 4px; margin-bottom: 0;">Verified personal, academic, and professional information stored in MongoDB.</p>
        </div>
        """, unsafe_allow_html=True)

        tab_pv, tab_pe = st.tabs(["👁️ View Profile", "✏️ Edit Profile Details"])

        with tab_pv:
            c_v1, c_v2 = st.columns([1.1, 1.9])
            with c_v1:
                st.markdown(f"""
                <div class="cream-card">
                    <h3 style="margin-top: 0; color: #2C1810;">{actual_student_name}</h3>
                    <div style="color: #5C381E; font-weight: 700;">{student.get('email') if student else ''}</div>
                    <hr style="border-color: #E6D8C8; margin: 10px 0;">
                    <div style="font-size: 0.88rem; color: #5D4037; line-height: 1.6;">
                        <b>Personal Information:</b><br/>
                        Phone: {student.get('phone') or 'Not provided'}<br/>
                        DOB: {student.get('dob') or 'Not provided'}<br/>
                        Gender: {student.get('gender') or 'Not provided'}<br/>
                    </div>
                    <hr style="border-color: #E6D8C8; margin: 10px 0;">
                    <div style="font-size: 0.88rem; color: #5D4037; line-height: 1.6;">
                        <b>Academic Information:</b><br/>
                        College: {student.get('college_name') or 'College of Engineering'}<br/>
                        Course: {student.get('course', 'B.Tech')}<br/>
                        Department: {student.get('branch', 'Computer Science')}<br/>
                        Year: {student.get('current_year', 4)} | Sem: {student.get('semester', 7)}<br/>
                        CGPA: <b style="color: #245731;">{student.get('cgpa', 0.0):.2f}</b><br/>
                        Backlogs: <b>{student.get('backlogs', 0)}</b>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Professional Information with LinkedIn Button
                st.markdown("#### 🌐 Professional Information")
                st.markdown(f"""
                <div class="cream-card">
                    <b>LinkedIn Profile:</b><br/>
                    {f"<a href='{student.get('linkedin_url')}' target='_blank' style='display:inline-block; background-color:#5C381E; color:#FFFFFF; padding:6px 14px; border-radius:6px; text-decoration:none; font-weight:600; font-size:0.85rem; margin-top:6px;'>View LinkedIn Profile ↗</a>" if student and student.get('linkedin_url') else "<span style='color:#7E6355; font-size:0.85rem;'>LinkedIn profile not added</span>"}
                    <br/><br/>
                    <b>GitHub Profile:</b><br/>
                    {f"<a href='{student.get('github_url')}' target='_blank' style='display:inline-block; background-color:#EFE4D6; color:#5C381E; padding:6px 14px; border-radius:6px; text-decoration:none; font-weight:600; font-size:0.85rem; margin-top:6px;'>View GitHub Profile ↗</a>" if student and student.get('github_url') else "<span style='color:#7E6355; font-size:0.85rem;'>GitHub profile not added</span>"}
                </div>
                """, unsafe_allow_html=True)

            with c_v2:
                st.markdown("#### ⚡ Technical Skills")
                actual_skills = student.get("skills", []) if student else []
                if not actual_skills:
                    st.info("No skills added yet.")
                else:
                    st.markdown(" ".join([f"<span class='skill-pill'>{s}</span>" for s in actual_skills]), unsafe_allow_html=True)

                st.markdown("---")
                st.markdown(f"#### 📁 Projects ({len(student.get('projects', [])) if student else 0})")
                projs = student.get("projects", []) if student else []
                if not projs:
                    st.caption("No projects added yet.")
                for p in projs:
                    st.markdown(f"• **{p.get('title')}** ({', '.join(p.get('technologies', []))}) — [GitHub]({p.get('github_url', '#')})")
                    if p.get("description"):
                        st.caption(p.get("description"))

                st.markdown("---")
                st.markdown(f"#### 🏢 Internships")
                interns = student.get("internships", []) if student else []
                if not interns:
                    st.info("ℹ️ **No internship yet**")
                else:
                    for it in interns:
                        st.markdown(f"• **{it.get('company_name')}** — {it.get('role')} ({it.get('duration_months')} months)")

                st.markdown("---")
                st.markdown(f"#### 📜 Certifications")
                certs = student.get("certifications", []) if student else []
                if not certs:
                    st.caption("No certifications added yet.")
                for ct in certs:
                    st.markdown(f"• **{ct.get('title')}** (Issuer: {ct.get('issuer')})")

        with tab_pe:
            with st.form("edit_profile_real"):
                st.markdown("##### 1. Personal & Professional Links")
                ep_name = st.text_input("Full Name", value=actual_student_name)
                c_ep1, c_ep2 = st.columns(2)
                with c_ep1:
                    ep_phone = st.text_input("Phone", value=student.get("phone", "") if student else "")
                    ep_dob = st.text_input("Date of Birth", value=student.get("dob", "") if student else "")
                with c_ep2:
                    ep_linkedin = st.text_input("LinkedIn Profile URL", value=student.get("linkedin_url", "") if student else "")
                    ep_github = st.text_input("GitHub Profile URL", value=student.get("github_url", "") if student else "")

                st.markdown("---")
                st.markdown("##### 2. Academic Information")
                c_ea1, c_ea2, c_ea3 = st.columns(3)
                with c_ea1:
                    ep_college = st.text_input("College", value=student.get("college_name", "") if student else "")
                    ep_course = st.selectbox("Course", ["B.Tech", "B.E", "M.Tech", "MCA", "B.Sc CS", "BCA"], index=0)
                with c_ea2:
                    ep_dept = st.selectbox("Department", ["Computer Science", "Information Technology", "Electronics", "Electrical", "Mechanical", "Civil"], index=0)
                    ep_sem = st.selectbox("Semester", [1, 2, 3, 4, 5, 6, 7, 8], index=int(student.get("semester", 7))-1 if student and 1 <= int(student.get("semester", 7)) <= 8 else 6)
                with c_ea3:
                    ep_cgpa = st.number_input("CGPA", min_value=0.0, max_value=10.0, value=float(student.get("cgpa", 7.50)) if student else 7.50, step=0.01)
                    ep_bk = st.number_input("Backlogs", min_value=0, max_value=10, value=int(student.get("backlogs", 0)) if student else 0)

                st.markdown("---")
                st.markdown("##### 3. Skills & Assessment Scores")
                curr_sk = student.get("skills", []) if student else []
                ep_skills = st.multiselect("Skills", sorted(list(set(curr_sk + ["Python", "Java", "C", "SQL", "React", "Node.js", "Docker", "Git", "Power BI", "Excel"]))), default=curr_sk)
                c_sc1, c_sc2, c_sc3 = st.columns(3)
                with c_sc1:
                    ep_apt = st.slider("Aptitude Score", 0.0, 100.0, float(student.get("aptitude_score", 70.0)) if student else 70.0)
                with c_sc2:
                    ep_tech = st.slider("Technical Score", 0.0, 100.0, float(student.get("technical_score", 75.0)) if student else 75.0)
                with c_sc3:
                    ep_comm = st.slider("Communication Score", 0.0, 100.0, float(student.get("communication_score", 70.0)) if student else 70.0)

                if st.form_submit_button("💾 Save Profile Updates to MongoDB", use_container_width=True):
                    upd_doc = {
                        "full_name": ep_name.strip(),
                        "phone": ep_phone.strip(),
                        "dob": ep_dob.strip(),
                        "linkedin_url": ep_linkedin.strip(),
                        "github_url": ep_github.strip(),
                        "college_name": ep_college.strip(),
                        "course": ep_course,
                        "branch": ep_dept,
                        "semester": ep_sem,
                        "cgpa": ep_cgpa,
                        "backlogs": ep_bk,
                        "skills": ep_skills,
                        "aptitude_score": ep_apt,
                        "technical_score": ep_tech,
                        "communication_score": ep_comm,
                        "updated_at": datetime.now().isoformat()
                    }
                    db.students.update_one({"email": st_email}, {"$set": upd_doc})
                    db.users.update_one({"email": st_email}, {"$set": {"full_name": ep_name.strip()}})
                    
                    # Update session
                    current_user["full_name"] = ep_name.strip()
                    st.session_state["logged_in_user"] = current_user
                    
                    st.success("Profile successfully saved in MongoDB!")
                    st.rerun()

    # ---------------- 3. PLACEMENT OPPORTUNITIES & COMPANY DETAILS PAGE ----------------
    elif student_menu == "🏢 Placement Opportunities":
        st.markdown("""
        <div class="cream-card">
            <h2 style="margin:0; color: #2C1810;">🏢 Placement Opportunities</h2>
            <p style="color: #5D4037; font-size: 0.92rem; margin-top: 4px; margin-bottom: 0;">Verified company campus drives with automated multi-factor eligibility evaluation.</p>
        </div>
        """, unsafe_allow_html=True)

        drives = list(db.placement_drives.find({"status": "Active"}))

        for drive in drives:
            d_id = str(drive["_id"])
            elig = EligibilityEvaluator.evaluate(student, drive) if student else {"is_eligible": False, "match_percentage": 0, "missing_criteria": ["No profile"]}
            is_elig = elig["is_eligible"]
            has_applied = db.applications.find_one({"student_id": student_id, "drive_id": d_id}) if student_id else None

            st.markdown(f"""
            <div class="cream-card-hover">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <span style="font-size: 1.3rem;">{drive.get('logo_icon', '🏢')}</span>
                        <span style="font-size: 1.2rem; font-weight: 700; color: #2C1810; margin-left: 6px;">{drive.get('company_name')}</span>
                        <div style="color: #5C381E; font-weight: 700; font-size: 1rem; margin-top: 2px;">{drive.get('role')}</div>
                        <div style="color: #5D4037; font-size: 0.85rem; margin-top: 3px;">
                            📍 {drive.get('location', 'Onsite')} | Industry: {drive.get('industry', 'Technology')} | 👥 Openings: <b>{drive.get('openings', 10)}</b> | 📅 Deadline: {drive.get('deadline', 'Open')}
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 1.45rem; font-weight: 800; color: #245731;">{drive.get('package_lpa', 0.0):.1f} LPA</div>
                        <div style="margin-top: 4px;">
                            {"<span class='badge-tag badge-eligible'>✓ Eligible</span>" if is_elig else "<span class='badge-tag badge-ineligible'>✕ Not Eligible</span>"}
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Detailed Expandable Comparison & Application Modal
            with st.expander(f"🔍 View Opportunity Details & Eligibility for {drive.get('company_name')}"):
                c_det_l, c_det_r = st.columns([1, 1.2])
                with c_det_l:
                    st.markdown("**Company Details:**")
                    st.write(f"• **Company:** {drive.get('company_name')}")
                    st.write(f"• **Role:** {drive.get('role')}")
                    st.write(f"• **Package:** {drive.get('package_lpa', 0.0):.1f} LPA")
                    st.write(f"• **Openings:** {drive.get('openings', 10)}")
                    st.write(f"• **Location:** {drive.get('location', 'Onsite')}")
                    st.write(f"• **Description:** {drive.get('description', 'Exciting engineering role.')}")

                with c_det_r:
                    st.markdown("**Your Eligibility Comparison:**")
                    
                    st_cgpa = float(student.get("cgpa", 0.0)) if student else 0.0
                    req_cgpa = float(drive.get("min_cgpa", 0.0))
                    cgpa_pass = st_cgpa >= req_cgpa

                    req_skills = drive.get("required_skills", [])
                    st_skills = student.get("skills", []) if student else []
                    skill_pass = any(s.lower() in [x.lower() for x in st_skills] for s in req_skills) if req_skills else True

                    st_bk = int(student.get("backlogs", 0)) if student else 0
                    max_bk = int(drive.get("max_backlogs", 0))
                    bk_pass = st_bk <= max_bk

                    st_apt = float(student.get("aptitude_score", 0.0)) if student else 0.0
                    req_apt = float(drive.get("min_aptitude_score", 0.0))
                    apt_pass = st_apt >= req_apt

                    comp_table = [
                        {"Requirement": "CGPA", "Required": f"{req_cgpa:.1f}+", "Your Profile": f"{st_cgpa:.2f}", "Status": "✓ Pass" if cgpa_pass else "✕ Fail"},
                        {"Requirement": "Required Skills", "Required": ", ".join(req_skills[:2]) if req_skills else "Open", "Your Profile": ", ".join(st_skills[:2]) if st_skills else "None", "Status": "✓ Pass" if skill_pass else "✕ Fail"},
                        {"Requirement": "Max Backlogs", "Required": f"{max_bk}", "Your Profile": f"{st_bk}", "Status": "✓ Pass" if bk_pass else "✕ Fail"},
                        {"Requirement": "Aptitude Score", "Required": f"{req_apt:.0f}%+", "Your Profile": f"{st_apt:.0f}%", "Status": "✓ Pass" if apt_pass else "✕ Fail"},
                    ]
                    st.dataframe(pd.DataFrame(comp_table), use_container_width=True)

                st.markdown("---")
                if has_applied:
                    st.button(f"✓ Already Applied (Status: {has_applied.get('status')})", key=f"opp_app_{d_id}", disabled=True)
                elif is_elig:
                    if st.button("🚀 Apply Now", key=f"opp_btn_{d_id}", type="primary"):
                        now_str = datetime.now().isoformat()
                        db.applications.insert_one({
                            "student_id": student_id,
                            "student_name": actual_student_name,
                            "student_email": st_email,
                            "roll_no": student.get("roll_no", ""),
                            "branch": student.get("branch", ""),
                            "cgpa": student.get("cgpa", 0.0),
                            "drive_id": d_id,
                            "company_name": drive.get("company_name"),
                            "role": drive.get("role"),
                            "package_lpa": drive.get("package_lpa", 0.0),
                            "status": "Applied",
                            "stage_history": [{"stage": "Applied", "timestamp": now_str, "updated_by": "Student", "remarks": "Applied via Placement Opportunities."}],
                            "remarks": "Application submitted successfully.",
                            "applied_at": now_str,
                            "updated_at": now_str
                        })
                        st.success(f"Application for {drive.get('company_name')} submitted successfully!")
                        st.rerun()
                else:
                    st.error(f"You are not currently eligible because your CGPA is below the required CGPA of {drive.get('min_cgpa', 0.0):.1f} or missing specific criteria ({', '.join(elig['missing_criteria'])}).")

            st.markdown("<br/>", unsafe_allow_html=True)

    # ---------------- 4. MY APPLICATIONS ----------------
    elif student_menu == "📑 My Applications":
        st.markdown("""
        <div class="cream-card">
            <h2 style="margin:0; color: #2C1810;">📑 My Applications Pipeline</h2>
            <p style="color: #5D4037; font-size: 0.92rem; margin-top: 4px; margin-bottom: 0;">Real-time tracking of all your campus applications across interview rounds.</p>
        </div>
        """, unsafe_allow_html=True)

        my_apps = list(db.applications.find({"student_id": student_id}).sort("applied_at", -1)) if student_id else []
        
        if not my_apps:
            st.info("You have not submitted any applications yet.")
        else:
            for app in my_apps:
                stt = app.get("status", "Applied")
                badge_class = "badge-eligible" if stt == "Selected" else ("badge-ineligible" if stt == "Rejected" else "badge-neutral")
                
                st.markdown(f"""
                <div class="cream-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h3 style="margin: 0; color: #2C1810;">{app.get('company_name')} — <span style="color: #5C381E;">{app.get('role')}</span></h3>
                            <div style="color: #5D4037; font-size: 0.85rem; margin-top: 3px;">Applied Date: {app.get('applied_at', '')[:10]} | Package: <b>{app.get('package_lpa', 0.0):.1f} LPA</b></div>
                        </div>
                        <div>
                            <span class="badge-tag {badge_class}" style="font-size: 0.85rem;">
                                {stt.upper()}
                            </span>
                        </div>
                    </div>
                    <div style="margin-top: 10px; background-color: #F7EFE6; padding: 10px 14px; border-radius: 6px; font-size: 0.88rem; border-left: 3px solid #5C381E;">
                        <b>Current Status:</b> <span style="color: #2C1810;">{app.get('remarks') or 'Under review.'}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # ---------------- 5. PLACEMENT READINESS & RADAR ----------------
    elif student_menu == "🎯 Placement Readiness":
        st.markdown(f"""
        <div class="cream-card">
            <h2 style="margin:0; color: #2C1810;">🎯 Placement Readiness & Prediction — {actual_student_name}</h2>
            <p style="color: #5D4037; font-size: 0.92rem; margin-top: 4px; margin-bottom: 0;">Multi-variable Gradient Boosting prediction engine with competency radar analysis.</p>
        </div>
        """, unsafe_allow_html=True)

        col_pr1, col_pr2 = st.columns([1, 1.5])
        with col_pr1:
            st.markdown(f"""
            <div class="cream-card" style="text-align: center;">
                <div style="font-size: 0.85rem; color: #5D4037; text-transform: uppercase; font-weight: 700;">Placement Readiness Score</div>
                <div style="font-size: 3.5rem; font-weight: 800; color: #5C381E; margin: 4px 0;">{pred['readiness_score']} / 100</div>
                <div class="badge-tag badge-neutral" style="font-size: 0.88rem; padding: 6px 14px;">
                    {pred['readiness_category']}
                </div>
                <hr style="border-color: #E6D8C8; margin: 16px 0;">
                <div style="font-size: 0.85rem; color: #5D4037;">Estimated Campus Package</div>
                <div style="font-size: 1.35rem; font-weight: 800; color: #245731;">{pred['estimated_package_range']}</div>
            </div>
            """, unsafe_allow_html=True)

        with col_pr2:
            st.markdown("#### 📊 Competency Radar Chart")
            radar_dict = pred["radar_scores"]
            if radar_dict:
                fig = go.Figure()
                fig.add_trace(go.Scatterpolar(
                    r=list(radar_dict.values()),
                    theta=list(radar_dict.keys()),
                    fill='toself',
                    fillcolor='rgba(92, 56, 30, 0.25)',
                    line=dict(color='#5C381E', width=2),
                    name='Competency'
                ))
                fig.update_layout(
                    polar=dict(
                        radialaxis=dict(visible=True, range=[0, 100], gridcolor="#E6D8C8"),
                        angularaxis=dict(gridcolor="#E6D8C8"),
                        bgcolor="#FFFDF9"
                    ),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#2C1810", family="Plus Jakarta Sans"),
                    margin=dict(l=30, r=30, t=10, b=10),
                    height=280
                )
                st.plotly_chart(fig, use_container_width=True)

    # ---------------- 6. RECOMMENDATIONS & CAREER MATCH ----------------
    elif student_menu == "💡 Recommendations & Career Match":
        st.markdown("""
        <div class="cream-card">
            <h2 style="margin:0; color: #2C1810;">💡 Personalized Recommendations & Career Match</h2>
            <p style="color: #5D4037; font-size: 0.92rem; margin-top: 4px; margin-bottom: 0;">Action plan and skill improvements generated from your profile data.</p>
        </div>
        """, unsafe_allow_html=True)

        for i, rec in enumerate(pred["recommendations"], start=1):
            st.markdown(f"""
            <div style="background-color: #FFFFFF; border: 1px solid #E6D8C8; border-left: 4px solid #5C381E; border-radius: 6px; padding: 12px 16px; margin-bottom: 8px; font-size: 0.92rem; color: #2C1810;">
                <span style="font-weight: 700; color: #5C381E;">Step {i}:</span> {rec}
            </div>
            """, unsafe_allow_html=True)

    # ---------------- 7. APTITUDE ASSESSMENT ----------------
    elif student_menu == "🧠 Aptitude Assessment":
        st.markdown("""
        <div class="cream-card">
            <h2 style="margin:0; color: #2C1810;">🧠 Aptitude Assessment & Practice Test</h2>
            <p style="color: #5D4037; font-size: 0.92rem; margin-top: 4px; margin-bottom: 0;">Test your Quantitative, Logical, and Verbal skills to update your placement readiness score.</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("aptitude_mini_test"):
            st.markdown("#### Quick 3-Question Practice Check")
            q1 = st.radio("1. (Quantitative) If a train travels 360 km in 4 hours, what is its speed in m/s?", ["25 m/s", "30 m/s", "20 m/s", "15 m/s"], index=0)
            q2 = st.radio("2. (Logical) Look at this series: 2, 6, 18, 54, ... What number comes next?", ["108", "148", "162", "216"], index=2)
            q3 = st.radio("3. (Verbal) Choose the word most similar to CANDID:", ["Secretive", "Frank / Honest", "Hesitant", "Polite"], index=1)

            if st.form_submit_button("Submit Assessment & Update Scores"):
                score = 0
                if q1 == "25 m/s": score += 33
                if q2 == "162": score += 34
                if q3 == "Frank / Honest": score += 33
                st.success(f"Assessment complete! You scored {score}/100.")
                db.students.update_one({"email": st_email}, {"$set": {"aptitude_score": float(score)}})
                st.rerun()

    # ---------------- 8. MY INTERNSHIPS ----------------
    elif student_menu == "💼 My Internships":
        st.markdown("""
        <div class="cream-card">
            <h2 style="margin:0; color: #2C1810;">💼 My Internships</h2>
            <p style="color: #5D4037; font-size: 0.92rem; margin-top: 4px; margin-bottom: 0;">Verified work experience and industry internships.</p>
        </div>
        """, unsafe_allow_html=True)

        interns = student.get("internships", []) if student else []
        if not interns:
            st.info("ℹ️ **No internship yet**")
        else:
            for it in interns:
                st.markdown(f"""
                <div class="cream-card">
                    <h3 style="margin:0; color: #2C1810;">{it.get('company_name')}</h3>
                    <div style="color: #5C381E; font-weight: 700;">{it.get('role')} ({it.get('duration_months')} Months)</div>
                    <div style="font-size: 0.88rem; color: #5D4037; margin-top: 6px;">{it.get('description')}</div>
                </div>
                """, unsafe_allow_html=True)

    # ---------------- 9. SETTINGS ----------------
    elif student_menu == "⚙️ Settings":
        st.markdown("""
        <div class="cream-card">
            <h2 style="margin:0; color: #2C1810;">⚙️ Account Settings</h2>
            <p style="color: #5D4037; font-size: 0.92rem; margin-top: 4px; margin-bottom: 0;">Manage your login credentials and notification preferences.</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("settings_form"):
            st.text_input("Account Email", value=st_email, disabled=True)
            new_p = st.text_input("Change Password", type="password", placeholder="Enter new password")
            if st.form_submit_button("Update Password"):
                if new_p:
                    db.users.update_one({"email": st_email}, {"$set": {"password_hash": hash_password(new_p)}})
                    st.success("Password updated successfully!")


# ==============================================================================
# LOGGED IN VIEW: ADMIN & PLACEMENT OFFICER PORTAL (REAL DATA ONLY)
# ==============================================================================

elif current_user and user_role == "admin":

    # ---------------- 1. ADMIN EXECUTIVE DASHBOARD ----------------
    if admin_menu == "📊 Executive Dashboard":
        st.markdown("""
        <div class="cream-card" style="background: linear-gradient(135deg, #F5EFEB 0%, #EAE0D2 100%);">
            <h1 style="margin:0; font-size: 1.85rem; color: #2C1810 !important;">📊 Placement Cell Executive Dashboard</h1>
            <p style="color: #5D4037; margin: 4px 0 0 0; font-size: 0.92rem;">Real-time campus recruitment intelligence and student readiness distributions.</p>
        </div>
        """, unsafe_allow_html=True)

        tot_st = db.students.count_documents({})
        tot_co = db.companies.count_documents({})
        tot_dr = db.placement_drives.count_documents({"status": "Active"})
        tot_ap = db.applications.count_documents({})
        tot_sl = db.applications.count_documents({"status": "Selected"})
        plc_rate = round((tot_sl / max(1, tot_st)) * 100, 1)

        ad1, ad2, ad3, ad4, ad5, ad6 = st.columns(6)
        ad1.markdown(f"""<div class="stat-box"><div class="stat-number">{tot_st}</div><div class="stat-label">Total Students</div></div>""", unsafe_allow_html=True)
        ad2.markdown(f"""<div class="stat-box"><div class="stat-number">{tot_co}</div><div class="stat-label">Companies</div></div>""", unsafe_allow_html=True)
        ad3.markdown(f"""<div class="stat-box"><div class="stat-number">{tot_dr}</div><div class="stat-label">Active Drives</div></div>""", unsafe_allow_html=True)
        ad4.markdown(f"""<div class="stat-box"><div class="stat-number">{tot_ap}</div><div class="stat-label">Applications</div></div>""", unsafe_allow_html=True)
        ad5.markdown(f"""<div class="stat-box"><div class="stat-number" style="color: #245731 !important;">{tot_sl}</div><div class="stat-label">Students Placed</div></div>""", unsafe_allow_html=True)
        ad6.markdown(f"""<div class="stat-box"><div class="stat-number" style="color: #8B5A2B !important;">{plc_rate}%</div><div class="stat-label">Placement Rate</div></div>""", unsafe_allow_html=True)

        st.markdown("<br/>", unsafe_allow_html=True)

        # Charts row
        c_ch1, c_ch2 = st.columns(2)
        with c_ch1:
            st.markdown("#### 📉 Application Status Funnel")
            stages_list = ["Applied", "Shortlisted", "Aptitude Test", "Technical Interview", "HR Interview", "Selected"]
            f_counts = [db.applications.count_documents({"status": s}) for s in stages_list]
            
            fig_fn = go.Figure(go.Funnel(
                y=stages_list,
                x=f_counts,
                textinfo="value+percent initial",
                marker=dict(color=["#5C381E", "#784F30", "#946743", "#B1825B", "#4A7C59", "#245731"])
            ))
            fig_fn.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#2C1810", family="Plus Jakarta Sans"),
                margin=dict(l=20, r=20, t=10, b=10),
                height=280
            )
            st.plotly_chart(fig_fn, use_container_width=True)

        with c_ch2:
            st.markdown("#### 🎯 Student Readiness Distribution")
            all_st_list = list(db.students.find({}))
            high_c = sum(1 for s in all_st_list if predictor.predict(s)["readiness_category"] == "High Readiness")
            mod_c = sum(1 for s in all_st_list if predictor.predict(s)["readiness_category"] == "Moderate Readiness")
            low_c = sum(1 for s in all_st_list if predictor.predict(s)["readiness_category"] == "Needs Improvement")

            fig_p = px.pie(
                values=[high_c, mod_c, low_c],
                names=["High Readiness (>=75%)", "Moderate Readiness (55-75%)", "Needs Improvement (<55%)"],
                color_discrete_sequence=["#245731", "#8B5A2B", "#872820"],
                hole=0.45
            )
            fig_p.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#2C1810", family="Plus Jakarta Sans"),
                margin=dict(l=20, r=20, t=10, b=10),
                height=280
            )
            st.plotly_chart(fig_p, use_container_width=True)

    # ---------------- 2. PLACEMENT DRIVES MANAGEMENT ----------------
    elif admin_menu == "🏢 Placement Drive Management":
        st.markdown("""
        <div class="cream-card">
            <h2 style="margin:0; color: #2C1810;">🏢 Placement Drive Management</h2>
            <p style="color: #5D4037; font-size: 0.92rem; margin-top: 4px; margin-bottom: 0;">Create and configure recruitment drives, define eligibility parameters, and inspect eligible student rankings.</p>
        </div>
        """, unsafe_allow_html=True)

        tab_ad_d1, tab_ad_d2 = st.tabs(["📋 Active Placement Drives", "➕ Create New Placement Drive"])

        with tab_ad_d1:
            all_d = list(db.placement_drives.find({}).sort("created_at", -1))
            for dr in all_d:
                dr_id = str(dr["_id"])
                ap_cnt = db.applications.count_documents({"drive_id": dr_id})
                
                st.markdown(f"""
                <div class="cream-card-hover">
                    <div style="display: flex; justify-content: space-between;">
                        <div>
                            <span style="font-size: 1.3rem;">{dr.get('logo_icon', '🏢')}</span>
                            <span style="font-size: 1.2rem; font-weight: 700; color: #2C1810; margin-left: 6px;">{dr.get('company_name')} — <span style="color: #5C381E;">{dr.get('role')}</span></span>
                            <div style="color: #5D4037; font-size: 0.85rem; margin-top: 4px;">Deadline: {dr.get('deadline', 'Open')} | Openings: {dr.get('openings', 10)} | Status: <b>{dr.get('status')}</b></div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 1.4rem; font-weight: 800; color: #245731;">{dr.get('package_lpa', 0.0):.1f} LPA</div>
                            <div style="color: #5C381E; font-size: 0.85rem; margin-top: 4px;"><b>{ap_cnt}</b> Applications</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                with st.expander(f"👥 View Ranked Eligible Students for {dr.get('company_name')}"):
                    all_s_list = list(db.students.find({}))
                    r_rows = []
                    for s in all_s_list:
                        ev = EligibilityEvaluator.evaluate(s, dr)
                        h_app = db.applications.find_one({"student_id": str(s["_id"]), "drive_id": dr_id})
                        r_rows.append({
                            "Name": s.get("full_name") or "Name not provided",
                            "Email": s.get("email"),
                            "Department": s.get("branch"),
                            "CGPA": s.get("cgpa"),
                            "Eligible": "✓ Yes" if ev["is_eligible"] else "✕ No",
                            "Match %": f"{ev['match_percentage']}%",
                            "Application Status": h_app.get("status") if h_app else "Not Applied"
                        })
                    st.dataframe(pd.DataFrame(r_rows), use_container_width=True)

        with tab_ad_d2:
            with st.form("new_drive_form"):
                ad_cname = st.text_input("Company Name", placeholder="e.g. Google, Microsoft, Adobe")
                ad_crole = st.text_input("Job Role", placeholder="e.g. Software Engineer (L3)")
                c_ad1, c_ad2, c_ad3 = st.columns(3)
                with c_ad1:
                    ad_pkg = st.number_input("Package (LPA)", min_value=1.0, max_value=100.0, value=15.0, step=0.5)
                    ad_min_cgpa = st.number_input("Minimum CGPA Cutoff", min_value=0.0, max_value=10.0, value=7.5, step=0.1)
                with c_ad2:
                    ad_min_apt = st.number_input("Minimum Aptitude Score", min_value=0.0, max_value=100.0, value=70.0, step=5.0)
                    ad_max_bk = st.number_input("Max Backlogs Allowed", min_value=0, max_value=10, value=0)
                with c_ad3:
                    ad_openings = st.number_input("Openings", min_value=1, max_value=500, value=20)
                    ad_logo = st.selectbox("Logo Icon", ["🏢", "💻", "🌐", "📦", "📈", "🏛️", "🚀"])
                
                ad_deadline = st.text_input("Application Deadline", value="2026-11-30")
                ad_skills = st.text_input("Required Skills (comma separated)", placeholder="Data Structures, Python, SQL, Git")
                ad_branches = st.multiselect("Eligible Branches", ["Computer Science", "Information Technology", "Electronics", "Electrical", "Mechanical", "Civil"], default=["Computer Science", "Information Technology"])
                ad_desc = st.text_area("Job Description")

                if st.form_submit_button("Publish Placement Drive", use_container_width=True):
                    if ad_cname and ad_crole:
                        db.placement_drives.insert_one({
                            "title": f"{ad_cname} - {ad_crole}",
                            "company_name": ad_cname,
                            "role": ad_crole,
                            "package_lpa": ad_pkg,
                            "min_cgpa": ad_min_cgpa,
                            "min_aptitude_score": ad_min_apt,
                            "max_backlogs": ad_max_bk,
                            "openings": ad_openings,
                            "logo_icon": ad_logo,
                            "required_skills": [s.strip() for s in ad_skills.split(",") if s.strip()],
                            "eligible_branches": ad_branches,
                            "location": "Hybrid / Onsite",
                            "deadline": ad_deadline,
                            "status": "Active",
                            "description": ad_desc,
                            "created_at": datetime.now().isoformat()
                        })
                        st.success("Placement drive published in MongoDB!")
                        st.rerun()

    # ---------------- 3. STUDENT DIRECTORY (REAL NAMES FROM MONGODB) ----------------
    elif admin_menu == "👨‍🎓 Student Directory & Portfolios":
        st.markdown("""
        <div class="cream-card">
            <h2 style="margin:0; color: #2C1810;">👨‍🎓 Student Directory & Portfolios</h2>
            <p style="color: #5D4037; font-size: 0.92rem; margin-top: 4px; margin-bottom: 0;">Searchable student roster with actual registered profiles and portfolio links.</p>
        </div>
        """, unsafe_allow_html=True)

        students_all = list(db.students.find({}))
        
        s_table = []
        for s in students_all:
            pr = predictor.predict(s)
            s_app = db.applications.find_one({"student_id": str(s["_id"])})
            s_table.append({
                "Name": s.get("full_name") or "Name not provided",
                "Email": s.get("email"),
                "Department": s.get("branch"),
                "Year": s.get("current_year", 4),
                "CGPA": s.get("cgpa"),
                "Skills": ", ".join(s.get("skills", [])[:3]),
                "Internship": f"{len(s.get('internships', []))} Internships",
                "Aptitude": f"{s.get('aptitude_score', 0):.0f}",
                "Readiness": f"{pr['readiness_score']}%",
                "Placement Status": s_app.get("status") if s_app else "Not Placed"
            })
        st.dataframe(pd.DataFrame(s_table), use_container_width=True)

        st.markdown("---")
        st.markdown("#### 🔍 View Student Portfolio")
        s_pick_name = st.selectbox("Choose Student:", [s.get("full_name") or "Name not provided" for s in students_all])
        s_ins = next((s for s in students_all if (s.get("full_name") or "Name not provided") == s_pick_name), None)
        
        if s_ins:
            pr_ins = predictor.predict(s_ins)
            c_ins1, c_ins2 = st.columns([1, 2])
            with c_ins1:
                st.markdown(f"""
                <div class="cream-card">
                    <h3 style="margin-top: 0; color: #2C1810;">{s_ins.get('full_name') or 'Name not provided'}</h3>
                    <div style="color: #5C381E;">{s_ins.get('email')}</div>
                    <div style="font-size: 0.85rem; color: #5D4037; margin-top: 8px; line-height: 1.6;">
                        College: <b>{s_ins.get('college_name') or 'N/A'}</b><br/>
                        Branch: <b>{s_ins.get('branch')}</b> (Year {s_ins.get('current_year', 4)})<br/>
                        CGPA: <b>{s_ins.get('cgpa')}</b> | Backlogs: <b>{s_ins.get('backlogs')}</b><br/>
                        Aptitude: <b>{s_ins.get('aptitude_score')}/100</b>
                    </div>
                    <hr style="border-color: #E6D8C8; margin: 10px 0;">
                    <div style="font-size: 0.9rem;">
                        Readiness: <b style="color: #245731;">{pr_ins['readiness_score']}%</b> ({pr_ins['readiness_category']})
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with c_ins2:
                st.markdown(f"**Skills:** {', '.join(s_ins.get('skills', []))}")
                st.markdown(f"**Projects ({len(s_ins.get('projects', []))}):**")
                for p in s_ins.get("projects", []):
                    st.markdown(f"• **{p.get('title')}**: {p.get('description', '')}")
                st.markdown(f"**Internships ({len(s_ins.get('internships', []))}):**")
                for it in s_ins.get("internships", []):
                    st.markdown(f"• **{it.get('company_name')}** ({it.get('role')})")

    # ---------------- 4. APPLICATION PIPELINE & STATUS UPDATES ----------------
    elif admin_menu == "📋 Applications & Stage Pipeline":
        st.markdown("""
        <div class="cream-card">
            <h2 style="margin:0; color: #2C1810;">📋 Candidate Application Pipeline & Stage Management</h2>
            <p style="color: #5D4037; font-size: 0.92rem; margin-top: 4px; margin-bottom: 0;">Advance candidates across interview stages and commit official remarks to MongoDB.</p>
        </div>
        """, unsafe_allow_html=True)

        all_apps_list = list(db.applications.find({}).sort("applied_at", -1))
        
        if not all_apps_list:
            st.info("No applications submitted yet.")
        else:
            for app in all_apps_list:
                app_id = str(app["_id"])
                
                st.markdown(f"""
                <div class="cream-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h3 style="margin: 0; color: #2C1810;">{app.get('student_name') or 'Name not provided'} ({app.get('branch')}, CGPA: {app.get('cgpa')})</h3>
                            <div style="color: #5C381E; font-weight: 700; font-size: 0.95rem; margin-top: 2px;">Applied for: <b>{app.get('company_name')}</b> — {app.get('role')} ({app.get('package_lpa', 0.0):.1f} LPA)</div>
                            <div style="color: #5D4037; font-size: 0.8rem; margin-top: 4px;">Applied: {app.get('applied_at', '')[:10]}</div>
                        </div>
                        <div>
                            <span class="badge-tag badge-neutral" style="font-size: 0.85rem;">
                                {app.get('status')}
                            </span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                with st.expander(f"⚙️ Update Stage & Feedback for {app.get('student_name') or 'Candidate'}"):
                    c_st1, c_st2 = st.columns([1, 2])
                    valid_stages = ["Applied", "Shortlisted", "Aptitude Test", "Technical Interview", "HR Interview", "Selected", "Rejected"]
                    curr_i = valid_stages.index(app.get("status", "Applied")) if app.get("status") in valid_stages else 0
                    
                    with c_st1:
                        new_stage_pick = st.selectbox("Status Stage", valid_stages, index=curr_i, key=f"adm_stg_{app_id}")
                    with c_st2:
                        stage_note = st.text_input("Placement Officer Remarks", value=app.get("remarks", ""), key=f"adm_rem_{app_id}")

                    if st.button("💾 Commit Stage Transition", key=f"adm_btn_{app_id}", type="primary"):
                        now_str = datetime.now().isoformat()
                        h_entry = {
                            "stage": new_stage_pick,
                            "timestamp": now_str,
                            "updated_by": "Placement Officer",
                            "remarks": stage_note or f"Advanced to {new_stage_pick}"
                        }
                        db.applications.update_one(
                            {"_id": ObjectId(app_id)},
                            {
                                "$set": {"status": new_stage_pick, "remarks": stage_note, "updated_at": now_str},
                                "$push": {"stage_history": h_entry}
                            }
                        )
                        st.success(f"Status updated to '{new_stage_pick}' in MongoDB!")
                        st.rerun()

    # ---------------- 5. RECRUITING PARTNERS DIRECTORY ----------------
    elif admin_menu == "🏭 Recruiting Partners Directory":
        st.markdown("""
        <div class="cream-card">
            <h2 style="margin:0; color: #2C1810;">🏭 Recruiting Partners Directory</h2>
            <p style="color: #5D4037; font-size: 0.92rem; margin-top: 4px; margin-bottom: 0;">Corporate relations and campus recruitment partners.</p>
        </div>
        """, unsafe_allow_html=True)

        comps = list(db.companies.find({}))
        for cp in comps:
            st.markdown(f"""
            <div class="cream-card-hover">
                <span style="font-size: 1.4rem;">{cp.get('logo_icon', '🏢')}</span>
                <span style="font-size: 1.2rem; font-weight: 700; color: #2C1810; margin-left: 8px;">{cp.get('name')}</span>
                <div style="color: #5C381E; font-weight: 700; font-size: 0.9rem; margin-top: 2px;">{cp.get('industry')} | 📍 {cp.get('location', 'India')}</div>
                <div style="color: #5D4037; font-size: 0.85rem; margin-top: 6px;">{cp.get('description', '')}</div>
                <div style="color: #7E6355; font-size: 0.8rem; margin-top: 6px;">Contact: {cp.get('contact_email')}</div>
            </div>
            """, unsafe_allow_html=True)

        with st.expander("➕ Register New Recruiting Partner"):
            with st.form("new_comp_reg"):
                cp_n = st.text_input("Company Name")
                cp_i = st.text_input("Industry", value="Information Technology")
                cp_l = st.text_input("Location", value="Bengaluru / Hyderabad")
                cp_logo = st.selectbox("Company Logo Icon", ["🏢", "💻", "🌐", "📦", "📈", "🏛️", "🚀"])
                cp_em = st.text_input("Campus Contact Email")
                cp_wb = st.text_input("Website URL")
                cp_ds = st.text_area("Description")
                if st.form_submit_button("Register Partner"):
                    if cp_n:
                        db.companies.insert_one({
                            "name": cp_n,
                            "industry": cp_i,
                            "location": cp_l,
                            "logo_icon": cp_logo,
                            "contact_email": cp_em,
                            "website": cp_wb,
                            "description": cp_ds,
                            "created_at": datetime.now().isoformat()
                        })
                        st.success(f"{cp_n} registered in MongoDB!")
                        st.rerun()
