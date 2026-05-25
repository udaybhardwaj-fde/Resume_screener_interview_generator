import os
import json
import datetime
from flask import Flask, render_template, request, jsonify
import re
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///analysis_history.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Database Model ---
class AnalysisResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    job_description = db.Column(db.Text, nullable=False)
    match_score = db.Column(db.Integer, nullable=False)
    analysis_data = db.Column(db.Text, nullable=False)
    decision_output = db.Column(db.Text, nullable=False)
    decision_type = db.Column(db.String(50), nullable=False)
    recruiter_summary = db.Column(db.Text, nullable=False)

@app.cli.command("init-db")
def init_db_command():
    """Creates the database tables."""
    db.create_all()
    print("Initialized the database.")

class ResumeAnalyzer:
    """Intelligent resume analyzer without external API dependency."""

    COMMON_SKILLS = {
        'programming': ['python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'golang', 'rust', 'php', 'ruby', 'swift'],
        'web': ['react', 'angular', 'vue', 'nodejs', 'express', 'django', 'flask', 'fastapi', 'html', 'css', 'jquery'],
        'data': ['sql', 'postgresql', 'mysql', 'mongodb', 'elasticsearch', 'hadoop', 'spark', 'pandas', 'numpy', 'scikit-learn'],
        'cloud': ['aws', 'azure', 'gcp', 'kubernetes', 'docker', 'terraform', 'jenkins', 'ci/cd'],
        'soft': ['communication', 'leadership', 'teamwork', 'problem solving', 'analytical', 'agile', 'scrum']
    }

    EXPERIENCE_KEYWORDS = {
        'senior': 8, 'lead': 7, 'principal': 10, 'manager': 6, 'architect': 9,
        'junior': 1, 'intern': 0.5, 'entry': 0.5, 'mid': 3, 'experienced': 5
    }

    @staticmethod
    def extract_skills(text):
        """Extract skills from text."""
        text_lower = text.lower()
        found_skills = set()

        for category, skills in ResumeAnalyzer.COMMON_SKILLS.items():
            for skill in skills:
                if skill in text_lower:
                    found_skills.add(skill)

        return list(found_skills)

    @staticmethod
    def extract_experience_years(text):
        """Extract years of experience from text."""
        text_lower = text.lower()

        # Look for explicit "X years" patterns
        pattern = r'(\d+)\s*(?:\+)?\s*years?'
        matches = re.findall(pattern, text_lower)
        if matches:
            return int(matches[0])

        # Look for experience level keywords
        for keyword, years in ResumeAnalyzer.EXPERIENCE_KEYWORDS.items():
            if keyword in text_lower:
                return years

        return 2  # default to 2 years

    @staticmethod
    def analyze(resume_text, job_description):
        """Analyze resume against job description."""
        resume_skills = set(ResumeAnalyzer.extract_skills(resume_text))
        job_skills = set(ResumeAnalyzer.extract_skills(job_description))
        resume_exp = ResumeAnalyzer.extract_experience_years(resume_text)
        job_exp = ResumeAnalyzer.extract_experience_years(job_description)

        # Calculate match score
        if job_skills:
            skill_match = len(resume_skills & job_skills) / len(job_skills) * 100
        else:
            skill_match = 50

        exp_match = min(100, (resume_exp / max(job_exp, 1)) * 100)

        # Check for education keywords
        education_keywords = ['bachelor', 'master', 'phd', 'degree', 'certification']
        has_education = any(kw in resume_text.lower() for kw in education_keywords)
        education_match = 80 if has_education else 40

        match_score = int((skill_match * 0.5 + exp_match * 0.3 + education_match * 0.2))
        match_score = min(100, max(0, match_score))

        # Identify missing requirements
        missing_requirements = list(job_skills - resume_skills)

        # Identify strengths
        strengths = [s for s in resume_skills if s in job_skills]
        if not strengths and resume_skills:
            strengths = list(resume_skills)[:3]

        return {
            "skills": list(resume_skills),
            "experience_years": resume_exp,
            "strengths": strengths or ["Good communication", "Problem solving"],
            "missing_requirements": missing_requirements or ["Domain-specific experience"],
            "match_score": match_score
        }

    @staticmethod
    def generate_interview_questions(analysis_data):
        """Generate interview questions based on analysis."""
        strengths = analysis_data.get('strengths', [])
        experience = analysis_data.get('experience_years', 2)

        base_questions = [
            "Can you walk us through your most challenging project and how you solved it?",
            "How do you stay updated with the latest industry trends and technologies?",
            "Tell us about your experience with our tech stack. Which part interests you most?",
            "How do you approach debugging complex issues in your code?",
            "Describe your experience working in a team environment. How do you handle conflicts?",
            "What's your approach to writing maintainable and scalable code?",
            "Can you share an example where you had to learn a new technology quickly?"
        ]

        if experience > 5:
            base_questions.extend([
                "How have you mentored junior developers in your previous roles?",
                "Tell us about a time you led a significant technical initiative or migration."
            ])

        return "\n".join([f"{i+1}. {q}" for i, q in enumerate(base_questions[:5])])

    @staticmethod
    def generate_rejection_reasoning(analysis_data):
        """Generate constructive feedback for rejection."""
        missing = analysis_data.get('missing_requirements', [])
        experience = analysis_data.get('experience_years', 2)
        score = analysis_data.get('match_score', 0)

        feedback = f"""Thank you for your interest in this position. While we appreciate your background,
we found that this role requires more specific expertise in the following areas:

"""
        if missing:
            feedback += f"- {', '.join(missing[:3])}\n\n"

        feedback += """To strengthen your candidacy for future opportunities, we recommend:

1. Gaining hands-on experience with the technologies mentioned above
2. Working on projects that align with the role's requirements
3. Pursuing relevant certifications or courses
4. Building a portfolio that showcases your technical skills

We encourage you to reapply once you've developed these skills. We also offer feedback sessions if you'd like to discuss your application in detail."""

        return feedback

    @staticmethod
    def generate_recruiter_summary(analysis_data, job_description, resume_text):
        """Generate a summary for the recruiter."""
        match_score = analysis_data['match_score']
        skills = analysis_data['strengths']
        experience = analysis_data['experience_years']

        if match_score > 75:
            status = "Strong Candidate"
            recommendation = "Highly recommended for interview"
        elif match_score > 60:
            status = "Good Candidate"
            recommendation = "Recommended for initial screening call"
        elif match_score > 45:
            status = "Potential Candidate"
            recommendation = "Consider for technical assessment"
        else:
            status = "Below Threshold"
            recommendation = "Not recommended at this time"

        summary = f"""Candidate Status: {status} ({match_score}% match)
Years of Experience: {experience}
Top Skills: {', '.join(skills[:3]) if skills else 'General background'}
Recommendation: {recommendation}

This candidate {'demonstrates strong alignment' if match_score > 70 else 'has potential' if match_score > 45 else 'does not align well'} with the role requirements.
Their experience level of {experience} years is {'well-suited' if experience >= 3 else 'entry to mid-level'} for this position."""

        return summary

def analyze_resume(resume_text, job_description):
    """Main analysis function."""
    analysis_data = ResumeAnalyzer.analyze(resume_text, job_description)
    score = analysis_data['match_score']

    if score > 70:
        interview_questions = ResumeAnalyzer.generate_interview_questions(analysis_data)
        decision_output = interview_questions
        result_key = "interview_questions"
    else:
        rejection_reasoning = ResumeAnalyzer.generate_rejection_reasoning(analysis_data)
        decision_output = rejection_reasoning
        result_key = "rejection_reasoning"

    recruiter_summary = ResumeAnalyzer.generate_recruiter_summary(analysis_data, job_description, resume_text)

    return analysis_data, decision_output, result_key, recruiter_summary

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    resume_text = data.get('resume')
    job_description = data.get('job_description')

    if not resume_text or not job_description:
        return jsonify({'error': 'Resume and Job Description cannot be empty.'}), 400

    try:
        analysis_data, decision_output, result_key, recruiter_summary = analyze_resume(resume_text, job_description)

        # Store results in the database
        new_analysis = AnalysisResult(
            job_description=job_description,
            match_score=analysis_data['match_score'],
            analysis_data=json.dumps(analysis_data),
            decision_output=decision_output,
            decision_type=result_key,
            recruiter_summary=recruiter_summary
        )
        db.session.add(new_analysis)
        db.session.commit()

        response_data = {
            'analysis': analysis_data,
            result_key: decision_output,
            'recruiter_summary': recruiter_summary
        }

        return jsonify(response_data), 200

    except Exception as e:
        print(f"Error during analysis: {e}")
        return jsonify({'error': f'An error occurred during analysis: {str(e)}'}), 500

@app.route('/history')
def history():
    """Renders the history page with all past analyses."""
    analyses = AnalysisResult.query.order_by(AnalysisResult.created_at.desc()).all()
    return render_template('history.html', analyses=analyses)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
