import os
import json
import datetime
from io import BytesIO
from flask import Flask, render_template, request, jsonify
import re
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError
from werkzeug.utils import secure_filename
from pii_validator import PIIValidator

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///analysis_history.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024
db = SQLAlchemy(app)
_db_initialized = False
ALLOWED_RESUME_EXTENSIONS = {'txt', 'pdf', 'docx'}
MAX_EXTRACTED_TEXT_LENGTH = 20000

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

@app.before_request
def ensure_database():
    """Create local SQLite tables automatically for first-time users."""
    global _db_initialized
    if not _db_initialized or not inspect(db.engine).has_table(AnalysisResult.__tablename__):
        db.create_all()
        _db_initialized = True

def save_analysis_result(analysis_result):
    """Save analysis history, recreating local tables if the SQLite file is incomplete."""
    try:
        db.session.add(analysis_result)
        db.session.commit()
    except OperationalError as exc:
        db.session.rollback()
        if 'no such table' not in str(exc).lower():
            raise

        db.create_all()
        db.session.add(analysis_result)
        db.session.commit()

def validate_payload(data):
    """Validate and normalize the incoming analysis payload."""
    if not isinstance(data, dict):
        return None, None, 'Request body must be valid JSON.'

    resume_text = (data.get('resume') or '').strip()
    job_description = (data.get('job_description') or '').strip()

    if not resume_text or not job_description:
        return None, None, 'Resume and Job Description cannot be empty.'

    if len(resume_text) < 40:
        return None, None, 'Resume text is too short to analyze reliably.'

    if len(job_description) < 40:
        return None, None, 'Job description is too short to analyze reliably.'

    if len(resume_text) > 20000 or len(job_description) > 10000:
        return None, None, 'Input is too large. Please shorten the resume or job description.'

    return resume_text, job_description, None

def allowed_resume_file(filename):
    """Return True when the uploaded resume extension is supported."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_RESUME_EXTENSIONS

def extract_text_from_resume(file_storage):
    """Extract text from an uploaded resume without storing the file."""
    original_filename = secure_filename(file_storage.filename or '')
    if not original_filename:
        return None, None, 'Please choose a resume file to upload.'

    if not allowed_resume_file(original_filename):
        return None, original_filename, 'Unsupported file type. Upload a .txt, .pdf, or .docx resume.'

    extension = original_filename.rsplit('.', 1)[1].lower()
    file_bytes = file_storage.read()

    if not file_bytes:
        return None, original_filename, 'Uploaded resume file is empty.'

    try:
        if extension == 'txt':
            try:
                extracted_text = file_bytes.decode('utf-8')
            except UnicodeDecodeError:
                extracted_text = file_bytes.decode('latin-1')
        elif extension == 'pdf':
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(file_bytes))
            extracted_text = '\n'.join(page.extract_text() or '' for page in reader.pages)
        else:
            from docx import Document

            document = Document(BytesIO(file_bytes))
            extracted_text = '\n'.join(paragraph.text for paragraph in document.paragraphs)
    except Exception as exc:
        return None, original_filename, f'Could not read resume file: {str(exc)}'

    extracted_text = re.sub(r'\n{3,}', '\n\n', extracted_text).strip()
    if not extracted_text:
        return None, original_filename, 'No readable text was found in the uploaded resume.'

    if len(extracted_text) > MAX_EXTRACTED_TEXT_LENGTH:
        extracted_text = extracted_text[:MAX_EXTRACTED_TEXT_LENGTH]

    return extracted_text, original_filename, None

class SafetyGuard:
    """Detect unsafe instructions before analysis."""

    PROMPT_INJECTION_PATTERNS = [
        r'ignore\s+(all\s+)?previous\s+instructions',
        r'disregard\s+(the\s+)?instructions',
        r'override\s+(the\s+)?system',
        r'you\s+are\s+now\s+',
        r'reveal\s+(your\s+)?prompt',
        r'print\s+(the\s+)?system\s+prompt',
        r'always\s+(return|respond)\s+.*100',
        r'give\s+.*(perfect|maximum)\s+score',
    ]

    @staticmethod
    def detect_prompt_injection(text):
        matches = []
        for pattern in SafetyGuard.PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                matches.append(pattern)
        return matches

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

        for skills in ResumeAnalyzer.COMMON_SKILLS.values():
            for skill in skills:
                if re.search(rf'\b{re.escape(skill)}\b', text_lower):
                    found_skills.add(skill)

        return sorted(found_skills)

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
        missing_requirements = sorted(job_skills - resume_skills)

        # Identify strengths
        strengths = sorted(s for s in resume_skills if s in job_skills)
        if not strengths and resume_skills:
            strengths = sorted(resume_skills)[:3]

        return {
            "skills": sorted(resume_skills),
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

    @staticmethod
    def generate_improvement_plan(analysis_data):
        """Generate a practical candidate improvement plan."""
        missing = analysis_data.get('missing_requirements', [])
        score = analysis_data.get('match_score', 0)
        focus_skills = missing[:3] or ['role-specific project experience']

        plan = [
            f"Priority focus: improve the {', '.join(focus_skills)} evidence in the resume.",
            "Add 2-3 measurable project bullets that connect experience directly to the job requirements.",
            "Create or highlight one portfolio project that demonstrates the strongest missing requirement.",
        ]

        if score < 50:
            plan.append("Apply after strengthening the core skill match; the current gap is material.")
        elif score < 70:
            plan.append("Consider a screening call if the role can support ramp-up time.")
        else:
            plan.append("Use the interview to validate depth in the listed strengths.")

        return "\n".join(f"{index}. {item}" for index, item in enumerate(plan, start=1))

def analyze_resume(resume_text, job_description):
    """Main analysis function."""
    analysis_data = ResumeAnalyzer.analyze(resume_text, job_description)
    score = analysis_data['match_score']

    if score >= 70:
        interview_questions = ResumeAnalyzer.generate_interview_questions(analysis_data)
        decision_output = interview_questions
        result_key = "interview_questions"
    else:
        rejection_reasoning = ResumeAnalyzer.generate_rejection_reasoning(analysis_data)
        decision_output = rejection_reasoning
        result_key = "rejection_reasoning"

    recruiter_summary = ResumeAnalyzer.generate_recruiter_summary(analysis_data, job_description, resume_text)
    improvement_plan = ResumeAnalyzer.generate_improvement_plan(analysis_data)

    return analysis_data, decision_output, result_key, recruiter_summary, improvement_plan

class RecruiterAssistant:
    """Small rule-based chat assistant for explaining screening results."""

    @staticmethod
    def answer(question, analysis_data):
        normalized_question = question.lower()
        score = analysis_data.get('match_score', 0)
        skills = analysis_data.get('skills', [])
        strengths = analysis_data.get('strengths', [])
        missing = analysis_data.get('missing_requirements', [])
        experience = analysis_data.get('experience_years', 'unknown')

        if any(term in normalized_question for term in ['score', 'match', 'fit']):
            return (
                f"The candidate has a {score}% match score. "
                f"The score is based on skill overlap, estimated experience, and education signals."
            )

        if any(term in normalized_question for term in ['missing', 'gap', 'weak', 'lack']):
            if missing:
                return f"The main gaps are: {', '.join(missing[:5])}."
            return "No major skill gaps were detected from the current job description."

        if any(term in normalized_question for term in ['strength', 'strong', 'skill']):
            if strengths:
                return f"The strongest matching signals are: {', '.join(strengths[:5])}."
            if skills:
                return f"The resume mentions these skills: {', '.join(skills[:5])}."
            return "I did not find strong skill signals in the resume text."

        if any(term in normalized_question for term in ['interview', 'question', 'ask']):
            if score >= 70:
                return (
                    "This candidate is worth interviewing. Focus questions on project depth, "
                    "hands-on ownership, debugging approach, and the strongest matched skills."
                )
            return (
                "I would not start with a deep technical interview yet. First validate whether "
                "the missing requirements can be ramped up quickly."
            )

        if any(term in normalized_question for term in ['reject', 'shortlist', 'hire', 'decision']):
            if score >= 75:
                return "Recommendation: shortlist for interview. The candidate shows strong alignment."
            if score >= 60:
                return "Recommendation: consider an initial screening call before a full technical round."
            return "Recommendation: do not shortlist yet unless the role can support a significant ramp-up."

        if any(term in normalized_question for term in ['experience', 'years', 'senior']):
            return f"The resume indicates approximately {experience} years of experience."

        if any(term in normalized_question for term in ['pii', 'privacy', 'safe', 'redact']):
            return (
                "The app checks for personal information and redacts common PII such as emails, "
                "phone numbers, addresses, SSNs, dates of birth, and LinkedIn URLs before analysis."
            )

        return (
            "I can help explain the score, strengths, missing requirements, interview focus, "
            "shortlist decision, experience level, or safety checks. Try asking about one of those."
        )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload-resume', methods=['POST'])
def upload_resume():
    """Extract resume text from an uploaded file."""
    if 'resume_file' not in request.files:
        return jsonify({'error': 'No resume file was uploaded.'}), 400

    resume_text, filename, error = extract_text_from_resume(request.files['resume_file'])
    if error:
        return jsonify({'error': error}), 400

    return jsonify({
        'filename': filename,
        'resume_text': resume_text,
        'char_count': len(resume_text)
    }), 200

@app.route('/chat-assistant', methods=['POST'])
def chat_assistant():
    """Answer recruiter questions about the latest analysis."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'Request body must be valid JSON.'}), 400

    question = (data.get('question') or '').strip()
    analysis_data = data.get('analysis') or {}

    if not question:
        return jsonify({'error': 'Question cannot be empty.'}), 400

    if not isinstance(analysis_data, dict) or 'match_score' not in analysis_data:
        return jsonify({'error': 'Run an analysis before asking the assistant.'}), 400

    return jsonify({
        'answer': RecruiterAssistant.answer(question, analysis_data)
    }), 200

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json(silent=True)
    resume_text, job_description, validation_error = validate_payload(data)

    if validation_error:
        return jsonify({'error': validation_error}), 400

    injection_matches = SafetyGuard.detect_prompt_injection(f"{resume_text}\n{job_description}")
    if injection_matches:
        return jsonify({
            'error': 'Unsafe prompt-injection style instructions were detected. Please remove instructions that try to override the analyzer.'
        }), 400

    # Validate and detect PII
    _, pii_info = PIIValidator.validate_resume(resume_text, strict=False)
    pii_warning = None
    if pii_info.get('warning'):
        pii_warning = {
            'message': pii_info.get('message'),
            'pii_types': pii_info.get('pii_types')
        }

    # Redact PII before analysis
    clean_resume, removed_pii = PIIValidator.redact_pii(resume_text)

    # Log only redaction metadata; never print raw PII to server logs.
    print("\n" + "="*80)
    print("PII VALIDATION & REDACTION DEBUG LOG")
    print("="*80)
    print("\n[CLEANED RESUME] (First 500 chars):")
    print(clean_resume[:500])
    print("\n[PII DETECTION SUMMARY]:")
    if removed_pii:
        print(PIIValidator.get_redaction_report(removed_pii))
    else:
        print("No PII detected - resume sent as-is")
    print("="*80 + "\n")

    try:
        analysis_data, decision_output, result_key, recruiter_summary, improvement_plan = analyze_resume(clean_resume, job_description)

        # Store results in the database
        new_analysis = AnalysisResult(
            job_description=job_description,
            match_score=analysis_data['match_score'],
            analysis_data=json.dumps(analysis_data),
            decision_output=decision_output,
            decision_type=result_key,
            recruiter_summary=recruiter_summary
        )
        save_analysis_result(new_analysis)

        response_data = {
            'analysis': analysis_data,
            result_key: decision_output,
            'recruiter_summary': recruiter_summary,
            'improvement_plan': improvement_plan,
            'pii_warning': pii_warning
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
    app.run(debug=os.getenv('FLASK_DEBUG') == '1', port=int(os.getenv('PORT', 5001)))
