import unittest
from datetime import datetime
from database import get_db, serialize_doc
from models import StudentProfile, PlacementDriveCreate, ApplicationCreate, ApplicationStatusUpdate
from ml_engine import predictor, EligibilityEvaluator
from auth import hash_password, verify_password
from seed_data import run_seed
from fastapi.testclient import TestClient
from backend_api import app

class TestPlacementSystem(unittest.TestCase):
    def setUp(self):
        self.db = get_db()
        self.client = TestClient(app)

    def test_01_database_and_seed(self):
        """Test database connection and demo dataset seeding with Recruiter role."""
        res = run_seed()
        self.assertTrue(res["success"])
        self.assertGreater(self.db.users.count_documents({}), 0)
        self.assertGreater(self.db.students.count_documents({}), 0)
        self.assertGreater(self.db.recruiters.count_documents({}), 0)
        self.assertGreater(self.db.placement_drives.count_documents({}), 0)
        print("[PASS] Database & Seed test passed!")

    def test_02_password_hashing(self):
        """Test password cryptographic hashing and verification."""
        raw_pw = "superSecretPassword123"
        hashed = hash_password(raw_pw)
        self.assertTrue(verify_password(raw_pw, hashed))
        self.assertFalse(verify_password("wrongPassword", hashed))
        print("[PASS] Secure Auth test passed!")

    def test_03_student_profile_and_ml_prediction(self):
        """Test student profile creation and ML readiness prediction."""
        student_data = {
            "email": "test.candidate@college.edu",
            "full_name": "Test Candidate",
            "roll_no": "22CS999",
            "branch": "Computer Science",
            "graduation_year": 2026,
            "cgpa": 8.90,
            "aptitude_score": 88.0,
            "technical_score": 90.0,
            "communication_score": 85.0,
            "skills": ["Python", "FastAPI", "React", "Data Structures", "Docker"],
            "projects": [
                {"title": "E-Commerce Microservice", "technologies": ["Python", "Docker"]}
            ],
            "certifications": [
                {"title": "AWS Cloud Practitioner", "issuer": "AWS"}
            ],
            "internships": [
                {"company_name": "Acme Tech", "role": "Software Intern", "duration_months": 3}
            ],
            "backlogs": 0,
            "target_role": "Full Stack Developer"
        }
        
        pred = predictor.predict(student_data)
        self.assertIn("readiness_score", pred)
        self.assertGreaterEqual(pred["readiness_score"], 70.0)
        self.assertEqual(pred["readiness_category"], "High Readiness")
        self.assertIn("radar_scores", pred)
        self.assertGreater(len(pred["strengths"]), 0)
        self.assertGreater(len(pred["recommendations"]), 0)
        print(f"[PASS] ML Prediction test passed! Score: {pred['readiness_score']}%, Category: {pred['readiness_category']}")

    def test_04_eligibility_evaluation(self):
        """Test company eligibility evaluation with precise reasons."""
        student_eligible = {
            "cgpa": 8.5,
            "aptitude_score": 80.0,
            "backlogs": 0,
            "branch": "Computer Science",
            "skills": ["Python", "Data Structures", "Algorithms", "C++"]
        }
        drive = {
            "min_cgpa": 7.5,
            "min_aptitude_score": 70.0,
            "max_backlogs": 0,
            "eligible_branches": ["Computer Science", "Information Technology"],
            "required_skills": ["Python", "Data Structures"]
        }
        eval_eligible = EligibilityEvaluator.evaluate(student_eligible, drive)
        self.assertTrue(eval_eligible["is_eligible"])
        self.assertGreater(len(eval_eligible["reasons"]), 0)

        # Ineligible student (CGPA below threshold)
        student_ineligible = {
            "cgpa": 6.8,
            "aptitude_score": 80.0,
            "backlogs": 0,
            "branch": "Computer Science",
            "skills": ["Python"]
        }
        eval_ineligible = EligibilityEvaluator.evaluate(student_ineligible, drive)
        self.assertFalse(eval_ineligible["is_eligible"])
        self.assertTrue(any("CGPA Mismatch" in m for m in eval_ineligible["missing_criteria"]))
        print("[PASS] Eligibility Engine test passed!")

    def test_05_recruiter_endpoints(self):
        """Test Recruiter authentication, stats, drives, candidate pool, and stage updates."""
        # 1. Login as Google recruiter
        login_res = self.client.post("/api/auth/login", json={
            "email": "recruiter@google.com",
            "password": "recruiter123"
        })
        self.assertEqual(login_res.status_code, 200)
        data = login_res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["user"]["role"], "recruiter")
        self.assertIsNotNone(data["user"]["recruiter_id"])
        recruiter_id = data["user"]["recruiter_id"]

        # 2. Recruiter stats
        stats_res = self.client.get(f"/api/recruiter/stats?recruiter_id={recruiter_id}")
        self.assertEqual(stats_res.status_code, 200)
        stats = stats_res.json()
        self.assertGreaterEqual(stats["total_drives"], 1)
        self.assertIn("candidate_pipeline", stats)

        # 3. Recruiter drives
        drives_res = self.client.get(f"/api/recruiter/drives?recruiter_id={recruiter_id}")
        self.assertEqual(drives_res.status_code, 200)
        drives = drives_res.json()
        self.assertGreater(len(drives), 0)
        drive_id = drives[0]["id"]

        # 4. Recruiter drive candidate breakdown (eligible vs ineligible)
        cand_res = self.client.get(f"/api/recruiter/drives/{drive_id}/eligible-candidates")
        self.assertEqual(cand_res.status_code, 200)
        cands = cand_res.json()
        self.assertIn("eligible", cands)
        self.assertIn("not_eligible", cands)

        # 5. Recruiter applications
        apps_res = self.client.get(f"/api/recruiter/applications?drive_id={drive_id}")
        self.assertEqual(apps_res.status_code, 200)
        apps = apps_res.json()
        if apps:
            app_id = apps[0]["id"]
            # 6. Recruiter stage progression
            stage_update_res = self.client.patch(
                f"/api/recruiter/applications/{app_id}/stage",
                json={"status": "Technical Interview", "remarks": "Passed technical test with flying colors"}
            )
            self.assertEqual(stage_update_res.status_code, 200)
            updated_app = stage_update_res.json()
            self.assertEqual(updated_app["status"], "Technical Interview")
            self.assertTrue(any(h.get("updated_by") == "Recruiter" for h in updated_app["stage_history"]))

        print("[PASS] Recruiter Portal REST API test passed!")

    def test_06_admin_endpoints(self):
        """Test Admin stats, analytics, students, recruiters, and CSV export."""
        stats_res = self.client.get("/api/admin/stats")
        self.assertEqual(stats_res.status_code, 200)
        stats = stats_res.json()
        self.assertIn("total_students", stats)
        self.assertIn("total_recruiters", stats)
        self.assertIn("total_companies", stats)
        self.assertIn("active_drives", stats)

        analytics_res = self.client.get("/api/admin/analytics")
        self.assertEqual(analytics_res.status_code, 200)
        analytics = analytics_res.json()
        self.assertIn("students_by_dept", analytics)
        self.assertIn("placement_by_year", analytics)
        self.assertIn("readiness_distribution", analytics)

        recruiters_res = self.client.get("/api/admin/recruiters")
        self.assertEqual(recruiters_res.status_code, 200)
        self.assertGreater(len(recruiters_res.json()), 0)

        csv_res = self.client.get("/api/admin/export/students.csv")
        self.assertEqual(csv_res.status_code, 200)
        self.assertIn("Full Name,Email", csv_res.text)
        print("[PASS] Admin Portal REST API test passed!")

if __name__ == "__main__":
    unittest.main()
