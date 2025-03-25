# AI Interview Agent - Mock Interview API

A Flask-based API that simulates an AI-powered interview process using GPT-4. The API generates professional interview questions, handles candidate responses, and provides detailed evaluations.

## 🚀 Quick Start

1. **Setup Environment**
```bash
python -m venv venv
# Windows
.\venv\Scripts\activate
# MacOS/Linux
source venv/bin/activate
pip install -r requirements.txt
```

2. **Configure Environment**
Create `.env` file:
```plaintext
OPENAI_API_KEY=your-api-key-here
```

3. **Run the Server**
```bash
python app.py
```
Server runs on `http://localhost:5022`

## 📚 API Documentation

### Base URL
```
http://localhost:5022
```

### Endpoints

#### 1. Start Interview
Initiates a new interview session.

**Endpoint:** `POST /start`

**Request Body:**
```json
{
    "job_role": "Software Engineer",
    "resume": "Candidate's resume text",
    "job_description": "Job posting description",
    "difficulty": "easy" // optional, defaults to "easy"
}
```

**Response:**
```json
{
    "question": "First interview question"
}
```

#### 2. Submit Response
Process candidate's response and continue the interview.

**Endpoint:** `POST /respond`

**Request Body:**
```json
{
    "response": "Candidate's answer"
}
```

**Response:**
```json
{
    "message": "Next question or interview completion message"
}
```

**Interview Completion Response:**
```json
{
    "status": "completed",
    "message": "Interview completed. Thank you for participating!"
}
```

#### 3. Get Evaluation
Retrieve the interview evaluation after completion.

**Endpoint:** `GET /evaluation`

**Response:**
```json
{
    "evaluation": "Detailed interview evaluation text"
}
```

#### 4. Get Interview Context
Retrieve the complete interview conversation.

**Endpoint:** `GET /context`

**Response:**
```json
[
    {
        "interviewer": "Question text"
    },
    {
        "candidate": "Answer text"
    }
]
```

### Interview States
The interview progresses through the following states:
1. Introduction
2. Resume Overview
3. Technical Evaluation
4. Behavioral Assessment
5. Cultural Fit
6. Closing

### Difficulty Levels
- **Easy**: 1 question per state
- **Medium**: 2 questions per state
- **Hard**: 3 questions per state

## 🔧 Technical Requirements

- Python 3.12.7
- OpenAI API Key
- Required packages (see requirements.txt)

## 📝 Notes

- The API uses GPT-4 for generating questions and evaluating responses
- Interview progress is tracked using a state machine
- All conversations are logged to `interview_log.json`
- Final evaluation is saved to `interview_evaluation.txt`
