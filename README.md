# 🎓 Smart Placement Management & Prediction System

A complete, hackathon-ready intelligent campus placement portal built with **FastAPI**, **Streamlit**, **MongoDB**, and **Scikit-Learn Machine Learning**.

---

## 🌟 Key Features

### 👨‍🎓 Student Portal
- **Interactive Dashboard**: Real-time placement readiness score gauge, target role fit indicator, and competency breakdown.
- **Competency Radar Chart**: 6-axis polar analysis (Academics, Technical Coding, General Aptitude, Communication, Project Experience, and Industry Exposure).
- **ML Placement Readiness Prediction**: Gradient Boosting & Random Forest scoring engine calculating placement probability, expected salary package range, strengths, weaknesses, and a 4-week step-by-step action plan.
- **Placement Opportunities & Real-Time Eligibility Evaluator**: Instant multi-condition match (CGPA cutoff, minimum aptitude, maximum backlogs, eligible branches, and required skill overlap) with explicit mismatch explanations.
- **Application Tracking Pipeline**: Real-time stage history tracking (`Applied → Shortlisted → Aptitude Test → Technical Interview → HR Interview → Selected / Rejected`).
- **Profile & Portfolio Management**: Full CRUD for academic details, skills inventory, multi-tier projects, certifications, and internships saved directly to MongoDB.

### 🏛️ Admin & Placement Cell Portal
- **Executive Analytics Dashboard**: High-level KPIs, Application Stage Funnel chart, Student Readiness Distribution, and Department breakdown.
- **Placement Drives Manager**: Create and configure recruitment drives with custom eligibility thresholds.
- **Eligible Candidate Inspector**: Search and rank candidates by eligibility match percentage for any drive.
- **Candidate Pipeline Manager**: Advance students across interview stages, add official placement cell remarks, and trigger real-time updates.
- **Recruiting Partners Directory**: Manage corporate relations and partner company profiles.

---

## 🏗️ Architecture

```
Frontend (Streamlit / Modern UI)
        ↓  (REST API / Direct ODM)
Backend (FastAPI REST Server)
        ↓
Machine Learning Engine (Scikit-Learn & Heuristic AI)
        ↓
MongoDB Database (users, students, companies, placement_drives, applications, predictions, recommendations)
```

---

## ⚙️ Environment Configuration (`.env`)

Create or update `.env` in the root folder:

```ini
# MongoDB Connection (Local instance or MongoDB Atlas)
MONGODB_URI=mongodb://127.0.0.1:27017/
DATABASE_NAME=smart_placement

# AI Configuration (Optional: system provides built-in ML intelligence if empty)
AI_API_KEY=your_ai_api_key_here
AI_PROVIDER=gemini

# Application Security
SECRET_KEY=smart_placement_secure_secret_key_2026_hackathon

# API Server Configuration
API_HOST=127.0.0.1
API_PORT=8000
API_BASE_URL=http://127.0.0.1:8000
```

> **Note on Resilient Database Mode:** If a local MongoDB daemon or Atlas URI is not active, the system automatically falls back to an in-memory `mongomock` database so that the application never crashes during live demos.

---

## 🚀 Quick Start Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Launch Streamlit Application (Frontend Portal)
```bash
streamlit run app.py
```
Open **`http://localhost:8501`** in your browser.

### 3. (Optional) Run FastAPI REST API Server
```bash
uvicorn backend_api:app --reload --port 8000
```
Interactive Swagger API docs available at **`http://127.0.0.1:8000/docs`**.

### 4. Run Automated Test Suite
```bash
python test_suite.py
```

---

## 🔑 Demo Accounts

| Role | Email | Password | Features / Notes |
|---|---|---|---|
| **Student** | `rahul.sharma@college.edu` | `student123` | High Readiness (8.75 CGPA, Full Stack) |
| **Student** | `priya.patel@college.edu` | `student123` | Selected Offer (9.20 CGPA, AI Engineer) |
| **Student** | `amit.kumar@college.edu` | `student123` | Moderate Readiness (6.80 CGPA, 1 Backlog) |
| **Student** | `ananya.verma@college.edu` | `student123` | DevOps Specialist (7.80 CGPA) |
| **Admin** | `admin@placement.edu` | `admin123` | Full Placement Cell Administration |
