import os
import pytest
import json
from app import app, db

# Set up the test client
@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:' # Use an in-memory DB for tests
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client

def test_index_page(client):
    """Test if the index page loads correctly."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"AI Resume Screener" in response.data

def test_history_page(client):
    """Test if the history page loads correctly."""
    response = client.get('/history')
    assert response.status_code == 200
    assert b"Analysis History" in response.data

def test_analyze_missing_data(client):
    """Test the /analyze endpoint with missing data."""
    # Test with missing resume
    response = client.post('/analyze', json={'job_description': 'A job', 'resume': ''})
    assert response.status_code == 400
    json_data = response.get_json()
    assert 'error' in json_data
    assert json_data['error'] == 'Resume and Job Description cannot be empty.'

    # Test with missing job description
    response = client.post('/analyze', json={'job_description': '', 'resume': 'A resume'})
    assert response.status_code == 400

def test_analyze_logic(client, monkeypatch):
    """
    Test the full analysis logic by mocking the LLM calls.
    This avoids making real API calls during tests, making them faster and free.
    """
    # --- Mock LLM Call 1: Simulate a high score ---
    def mock_llm_high_score(prompt, max_tokens=None):
        if "Extract the candidate's skills" in prompt:
            return json.dumps({
                "skills": ["Python", "Flask"],
                "experience_years": 5,
                "strengths": ["API Design"],
                "missing_requirements": [],
                "match_score": 85
            })
        if "generate 5 advanced technical interview questions" in prompt:
            return "Here are some advanced questions..."
        if "write a concise summary for the recruiter" in prompt:
            return "This is a great candidate."
        return ""

    # Apply the mock
    monkeypatch.setattr('app.call_llm', mock_llm_high_score)

    # Make the test request
    response = client.post('/analyze', json={
        'job_description': 'Python Developer job',
        'resume': 'Experienced Python developer resume'
    })

    assert response.status_code == 200
    json_data = response.get_json()

    # Assert the output for a high-scoring candidate
    assert json_data['analysis']['match_score'] == 85
    assert 'interview_questions' in json_data
    assert json_data['interview_questions'] == "Here are some advanced questions..."
    assert json_data['recruiter_summary'] == "This is a great candidate."

def test_analyze_logic_low_score(client, monkeypatch):
    """
    Test the full analysis logic for a low-scoring candidate.
    """
    # --- Mock LLM Call 2: Simulate a low score ---
    def mock_llm_low_score(prompt, max_tokens=None):
        if "Extract the candidate's skills" in prompt:
            return json.dumps({
                "skills": ["Python"],
                "experience_years": 1,
                "strengths": [],
                "missing_requirements": ["Flask", "SQLAlchemy"],
                "match_score": 45
            })
        if "generate a polite rejection reasoning" in prompt:
            return "Thank you for your interest, but we are looking for more experience."
        if "write a concise summary for the recruiter" in prompt:
            return "This candidate is not a strong match."
        return ""

    # Apply the mock
    monkeypatch.setattr('app.call_llm', mock_llm_low_score)

    # Make the test request
    response = client.post('/analyze', json={
        'job_description': 'Senior Python Developer job',
        'resume': 'Junior Python developer resume'
    })

    assert response.status_code == 200
    json_data = response.get_json()

    # Assert the output for a low-scoring candidate
    assert json_data['analysis']['match_score'] == 45
    assert 'rejection_reasoning' in json_data
    assert json_data['rejection_reasoning'] == "Thank you for your interest, but we are looking for more experience."
    assert json_data['recruiter_summary'] == "This candidate is not a strong match."


# ```

# #### How to Run Automated Tests

# 1.  Make sure your virtual environment is active.
# 2.  Open your terminal in the project root.
# 3.  Run `pytest`:

# ```bash
# pytest
