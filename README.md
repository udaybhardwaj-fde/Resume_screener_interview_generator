# AI Resume Screener & Interview Generator

This Flask application uses a Large Language Model (LLM) to analyze a candidate's resume against a job description. It extracts key information, calculates a match score, and then either generates technical interview questions for promising candidates or provides constructive feedback for those who are not a strong match.

## Features

- **Resume Analysis**: Extracts skills, experience, strengths, and missing requirements from a resume.
- **Match Scoring**: Calculates a percentage score based on the alignment between the resume and the job description.
- **Conditional Logic**:
  - If the score is > 70%, it generates advanced technical interview questions.
  - If the score is <= 70%, it provides polite rejection reasoning and suggestions for improvement.
- **Recruiter Summary**: Generates a concise summary for the hiring manager.
- **Database Storage**: Saves every analysis to a local SQLite database.
- **History Page**: A page to view all past analysis results.
- **Web Interface**: Simple UI to input the job description and resume text.

## Setup Steps

### 1. Clone the Repository

Clone this project to your local machine.

### 2. Create a Virtual Environment

It's recommended to use a virtual environment to manage project dependencies.

```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

### 3. Install Dependencies

Install the required Python packages using pip.

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

1.  Create a file named `.env` in the project root directory.
2.  Add your Hugging Face API key to the `.env` file:
    ```
    HUGGINGFACE_API_KEY="your_huggingface_api_key_here"
    ```
    Replace `"your_huggingface_api_key_here"` with your actual API token from Hugging Face.

### 5. Initialize the Database

Run the following command in your terminal to create the `analysis_history.db` file and set up the necessary tables. This only needs to be done once.

```bash
# For Windows
flask init-db
```

### 6. Run the Application

Start the Flask development server.

```bash
python app.py
```

The application will be running at `http://127.0.0.1:5001`. Open this URL in your web browser to use the tool.