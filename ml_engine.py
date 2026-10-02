import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Tuple
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor

logger = logging.getLogger("SmartPlacementMLEngine")

ROLE_SKILL_MAP = {
    "Software Engineer": ["Data Structures", "Algorithms", "Python", "Java", "C++", "SQL", "Git", "System Design", "OOP"],
    "Full Stack Developer": ["React", "Node.js", "JavaScript", "TypeScript", "HTML/CSS", "MongoDB", "Express", "REST APIs", "Git"],
    "Frontend Engineer": ["React", "JavaScript", "HTML/CSS", "TypeScript", "Tailwind CSS", "Redux", "UI/UX", "Next.js"],
    "Backend Developer": ["Python", "FastAPI", "Node.js", "PostgreSQL", "MongoDB", "Docker", "Redis", "Microservices", "REST APIs"],
    "Data Scientist / AI Engineer": ["Python", "Machine Learning", "Pandas", "NumPy", "Scikit-Learn", "TensorFlow", "SQL", "Deep Learning", "NLP"],
    "Data Analyst": ["Python", "SQL", "Tableau", "Power BI", "Excel", "Data Visualization", "Pandas", "Statistics"],
    "Cloud / DevOps Engineer": ["Linux", "Docker", "Kubernetes", "AWS", "CI/CD", "Terraform", "Git", "Python", "Bash"],
    "Cybersecurity Analyst": ["Network Security", "Cryptography", "Linux", "Ethical Hacking", "Python", "Wireshark", "SIEM", "OWASP"]
}

class PlacementPredictor:
    def __init__(self):
        self.regressor = None
        self.classifier = None

    def _ensure_models(self):
        if self.regressor is not None:
            return
        np.random.seed(42)
        n_samples = 250
        cgpa = np.random.uniform(5.0, 10.0, n_samples)
        aptitude = np.random.uniform(30.0, 100.0, n_samples)
        technical = np.random.uniform(30.0, 100.0, n_samples)
        comms = np.random.uniform(30.0, 100.0, n_samples)
        projects = np.random.randint(0, 6, n_samples)
        internships = np.random.randint(0, 4, n_samples)
        certs = np.random.randint(0, 5, n_samples)
        skills_count = np.random.randint(1, 12, n_samples)
        backlogs = np.random.choice([0, 1, 2, 3, 4], size=n_samples, p=[0.7, 0.15, 0.08, 0.04, 0.03])

        X = np.column_stack([cgpa, aptitude, technical, comms, projects, internships, certs, skills_count, backlogs])
        y_score = (
            (cgpa / 10.0) * 22.0 +
            (technical / 100.0) * 25.0 +
            (aptitude / 100.0) * 18.0 +
            (comms / 100.0) * 15.0 +
            np.minimum(projects * 3.0, 9.0) +
            np.minimum(internships * 4.0, 8.0) +
            np.minimum(certs * 1.5, 4.5) +
            np.minimum(skills_count * 0.8, 6.0) -
            (backlogs * 7.5)
        )
        y_score = np.clip(y_score, 10.0, 99.0)
        self.regressor = GradientBoostingRegressor(n_estimators=15, random_state=42)
        self.regressor.fit(X, y_score)

    def extract_features(self, student_data: Dict[str, Any]) -> np.ndarray:
        cgpa = float(student_data.get("cgpa", 0.0) or 0.0)
        aptitude = float(student_data.get("aptitude_score", 0.0) or 0.0)
        technical = float(student_data.get("technical_score", 0.0) or 0.0)
        comms = float(student_data.get("communication_score", 0.0) or 0.0)
        
        projects = len(student_data.get("projects", []))
        internships = len(student_data.get("internships", []))
        certs = len(student_data.get("certifications", []))
        skills = len(student_data.get("skills", []))
        backlogs = int(student_data.get("backlogs", 0) or 0)

        return np.array([[cgpa, aptitude, technical, comms, projects, internships, certs, skills, backlogs]])

    def predict(self, student_data: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure_models()
        features = self.extract_features(student_data)
        
        # Predicted Score (0 - 100)
        raw_score = float(self.regressor.predict(features)[0])
        score = round(max(5.0, min(99.0, raw_score)), 1)

        # Categorization
        if score >= 75.0:
            category = "High Readiness"
            pkg_range = "8.0 - 22.0 LPA"
        elif score >= 55.0:
            category = "Moderate Readiness"
            pkg_range = "4.5 - 8.5 LPA"
        else:
            category = "Needs Improvement"
            pkg_range = "3.0 - 5.0 LPA"

        # Radar / Breakdown Scores
        cgpa = float(student_data.get("cgpa", 0.0) or 0.0)
        aptitude = float(student_data.get("aptitude_score", 0.0) or 0.0)
        technical = float(student_data.get("technical_score", 0.0) or 0.0)
        comms = float(student_data.get("communication_score", 0.0) or 0.0)
        num_proj = len(student_data.get("projects", []))
        num_intern = len(student_data.get("internships", []))
        num_skills = len(student_data.get("skills", []))
        backlogs = int(student_data.get("backlogs", 0) or 0)

        radar = {
            "Academics (CGPA)": min(100.0, round((cgpa / 10.0) * 100, 1)),
            "Technical Aptitude": min(100.0, round(technical, 1)),
            "General Aptitude": min(100.0, round(aptitude, 1)),
            "Communication": min(100.0, round(comms, 1)),
            "Project Experience": min(100.0, round(num_proj * 25.0, 1)),
            "Industry Exposure": min(100.0, round(num_intern * 40.0, 1))
        }

        # Strengths & Weaknesses analysis
        strengths = []
        weaknesses = []

        if cgpa >= 8.0:
            strengths.append(f"Strong academic foundation with a CGPA of {cgpa:.2f}/10.0")
        elif cgpa < 6.5:
            weaknesses.append(f"CGPA ({cgpa:.2f}) is below tier-1 company cutoffs (typically 7.0+)")

        if technical >= 75.0:
            strengths.append(f"High technical test performance ({technical:.1f}/100)")
        elif technical < 60.0:
            weaknesses.append(f"Technical aptitude score ({technical:.1f}/100) needs enhancement through DSA & coding practice")

        if aptitude >= 75.0:
            strengths.append(f"Solid problem solving & quantitative aptitude ({aptitude:.1f}/100)")
        elif aptitude < 60.0:
            weaknesses.append(f"Aptitude score ({aptitude:.1f}/100) may bottleneck initial screening rounds")

        if comms >= 75.0:
            strengths.append(f"Excellent communication & HR interview readiness ({comms:.1f}/100)")
        elif comms < 60.0:
            weaknesses.append(f"Communication rating ({comms:.1f}/100) could impact managerial & HR rounds")

        if num_proj >= 2:
            strengths.append(f"Demonstrated hands-on experience with {num_proj} practical project(s)")
        else:
            weaknesses.append("Lack of multi-tier portfolio projects showcasing real-world problem solving")

        if num_intern >= 1:
            strengths.append(f"Practical industry experience with {num_intern} completed internship(s)")
        else:
            weaknesses.append("No prior industry internship on record")

        if backlogs > 0:
            weaknesses.append(f"Candidate has {backlogs} active backlog(s), which disqualifies from certain strict placement drives")
        else:
            strengths.append("Clean academic record with 0 active backlogs")

        if not strengths:
            strengths.append("Consistent dedication to professional growth and learning")
        if not weaknesses:
            weaknesses.append("Maintain continuous competitive coding to preserve top-tier placement standing")

        # Target Role Match
        target_role = student_data.get("target_role", "Software Engineer") or "Software Engineer"
        role_fit = self.evaluate_role_fit(student_data, target_role)

        # Generate actionable recommendations
        recommendations = self.generate_recommendations(student_data, strengths, weaknesses, role_fit)

        return {
            "readiness_score": score,
            "readiness_category": category,
            "estimated_package_range": pkg_range,
            "radar_scores": radar,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "recommendations": recommendations,
            "target_role_fit": role_fit,
            "generated_at": datetime.now().isoformat(),
            "disclaimer": "This prediction is an estimated readiness assessment based on academic, technical, and extracurricular metrics, not a guaranteed employment outcome."
        }

    def evaluate_role_fit(self, student_data: Dict[str, Any], target_role: str) -> Dict[str, Any]:
        req_skills = ROLE_SKILL_MAP.get(target_role, ROLE_SKILL_MAP["Software Engineer"])
        student_skills = [s.strip().lower() for s in student_data.get("skills", []) if s]
        
        matched = []
        missing = []

        for req in req_skills:
            if any(req.lower() in s or s in req.lower() for s in student_skills):
                matched.append(req)
            else:
                missing.append(req)

        fit_percentage = round((len(matched) / len(req_skills)) * 100, 1) if req_skills else 0.0

        return {
            "target_role": target_role,
            "fit_percentage": fit_percentage,
            "matched_skills": matched,
            "missing_skills": missing,
            "total_benchmark_skills": len(req_skills)
        }

    def generate_recommendations(self, student_data: Dict[str, Any], strengths: List[str], weaknesses: List[str], role_fit: Dict[str, Any]) -> List[str]:
        recs = []
        
        # Skill-based recommendations
        missing = role_fit.get("missing_skills", [])
        if missing:
            recs.append(f"Master core skills for {role_fit.get('target_role')}: Focus on {', '.join(missing[:3])}.")

        # Scores recommendations
        tech = float(student_data.get("technical_score", 0.0) or 0.0)
        if tech < 70.0:
            recs.append("Practice at least 3 LeetCode / HackerRank problems daily covering Trees, Dynamic Programming, and Graph algorithms.")

        apt = float(student_data.get("aptitude_score", 0.0) or 0.0)
        if apt < 70.0:
            recs.append("Dedicate 45 minutes daily to quantitative aptitude and logical reasoning mock tests on platforms like IndiaBIX / GeeksforGeeks.")

        proj_count = len(student_data.get("projects", []))
        if proj_count < 2:
            recs.append(f"Build and deploy a full-stack, production-grade project related to {role_fit.get('target_role')} with a public GitHub repository and live demo.")

        intern_count = len(student_data.get("internships", []))
        if intern_count == 0:
            recs.append("Apply for summer/winter internships or contribute to verified open-source GitHub repositories to validate team collaboration skills.")

        comms = float(student_data.get("communication_score", 0.0) or 0.0)
        if comms < 70.0:
            recs.append("Participate in peer mock technical and HR interviews to refine STAR-method storytelling for behavioral questions.")

        recs.append("Keep your resume ATS-optimized with quantifiable achievements (e.g. 'Improved query performance by 40%').")
        return recs


class EligibilityEvaluator:
    @staticmethod
    def evaluate(student_data: Dict[str, Any], drive_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates student against placement drive criteria and returns:
        - is_eligible: bool
        - reasons: list of passes / breakdown
        - missing_criteria: list of failures with exact numerical/skill mismatch
        - match_percentage: float (0-100)
        """
        reasons = []
        missing_criteria = []
        total_checks = 0
        passed_checks = 0

        student_cgpa = float(student_data.get("cgpa", 0.0) or 0.0)
        min_cgpa = float(drive_data.get("min_cgpa", 0.0) or 0.0)
        
        student_aptitude = float(student_data.get("aptitude_score", 0.0) or 0.0)
        min_aptitude = float(drive_data.get("min_aptitude_score", 0.0) or 0.0)

        student_backlogs = int(student_data.get("backlogs", 0) or 0)
        max_backlogs = int(drive_data.get("max_backlogs", 0) or 0)

        student_branch = (student_data.get("branch") or "").strip()
        eligible_branches = drive_data.get("eligible_branches") or []

        student_skills = [s.strip().lower() for s in student_data.get("skills", []) if s]
        required_skills = drive_data.get("required_skills") or []

        # 1. CGPA Check
        total_checks += 1
        if student_cgpa >= min_cgpa:
            passed_checks += 1
            reasons.append(f"✓ CGPA Requirement Met: Candidate has {student_cgpa:.2f} (Required: {min_cgpa:.2f}+)")
        else:
            missing_criteria.append(f"✕ CGPA Mismatch: Required CGPA is {min_cgpa:.2f}, but candidate has {student_cgpa:.2f}")

        # 2. Aptitude Check
        total_checks += 1
        if student_aptitude >= min_aptitude:
            passed_checks += 1
            reasons.append(f"✓ Aptitude Threshold Met: Candidate scored {student_aptitude:.1f}/100 (Required: {min_aptitude:.1f}+)")
        else:
            missing_criteria.append(f"✕ Aptitude Threshold: Required score is {min_aptitude:.1f}/100, but candidate scored {student_aptitude:.1f}/100")

        # 3. Backlog Check
        total_checks += 1
        if student_backlogs <= max_backlogs:
            passed_checks += 1
            reasons.append(f"✓ Backlog Condition Satisfied: {student_backlogs} backlog(s) (Maximum allowed: {max_backlogs})")
        else:
            missing_criteria.append(f"✕ Backlog Limit Exceeded: Maximum allowed backlogs is {max_backlogs}, but candidate has {student_backlogs}")

        # 4. Branch Check (if specified)
        if eligible_branches:
            total_checks += 1
            if any(b.lower() == student_branch.lower() or student_branch.lower() in b.lower() for b in eligible_branches):
                passed_checks += 1
                reasons.append(f"✓ Eligible Branch: {student_branch}")
            else:
                missing_criteria.append(f"✕ Branch Restriction: Drive is restricted to {', '.join(eligible_branches)}, but student is in '{student_branch}'")

        # 5. Required Skills Match
        if required_skills:
            total_checks += 1
            matched_req = []
            unmatched_req = []
            for req in required_skills:
                if any(req.lower() in s or s in req.lower() for s in student_skills):
                    matched_req.append(req)
                else:
                    unmatched_req.append(req)
            
            skill_pct = (len(matched_req) / len(required_skills)) * 100 if required_skills else 100.0
            if skill_pct >= 50.0:  # Candidate has at least half required skills
                passed_checks += 1
                reasons.append(f"✓ Skill Match ({skill_pct:.0f}%): Has {len(matched_req)}/{len(required_skills)} required skills ({', '.join(matched_req)})")
            else:
                missing_criteria.append(f"✕ Skill Gap: Missing required skills ({', '.join(unmatched_req)})")

        is_eligible = len(missing_criteria) == 0
        match_percentage = round((passed_checks / max(1, total_checks)) * 100, 1)

        return {
            "is_eligible": is_eligible,
            "match_percentage": match_percentage,
            "reasons": reasons,
            "missing_criteria": missing_criteria,
            "student_cgpa": student_cgpa,
            "required_cgpa": min_cgpa,
            "student_aptitude": student_aptitude,
            "required_aptitude": min_aptitude,
            "student_backlogs": student_backlogs,
            "max_backlogs": max_backlogs
        }


# Global singleton instance
predictor = PlacementPredictor()
