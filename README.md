# AI Interview Agent - Mock Interview API

A Flask-based API that simulates an AI-powered interview process using GPT-4. The API generates professional interview questions, handles candidate responses, and provides detailed evaluations.

## 🚀 Quick Start

### Prerequisites

- Python 3.12.7
- OpenAI API Key
- Tavily API Key
- Git (optional)

### Installation Steps

1. **Clone the Repository**

```bash
git clone <repository-url>
cd <project-directory>
```

2. **Setup Environment**

```bash
python -m venv venv
# Windows
.\venv\Scripts\activate
# MacOS/Linux
source venv/bin/activate
pip install -r requirements.txt
```

3. **Configure Environment**
   Create `.env` file in the root directory:

```plaintext
# Required API Keys
OPENAI_API_KEY=your-openai-api-key-here
TAVILY_API_KEY=your-tavily-api-key-here
GROQ_API_KEY=your-groq-api-key-here  # Required only if using Groq
NEBIUS_API_KEY=your-nebius-api-key-here  # Required only if using Nebius

# LLM Configuration
LLM_PROVIDER=openai  # Options: "openai", "groq", or "nebius"
LLM_MODEL=gpt-4     # Model name (e.g., "gpt-4" for OpenAI, "mixtral-8x7b-32768" for Groq, "meta-llama/Meta-Llama-3.1-70B-Instruct-fast" for Nebius)
```

**Note:** 
- For OpenAI, use models like "gpt-4", "gpt-3.5-turbo"
- For Groq, use models like "mixtral-8x7b-32768", "llama2-70b-4096"
- For Nebius, use models like "meta-llama/Meta-Llama-3.1-70B-Instruct-fast"
- You only need to set the API key for the provider you're using
- Default provider is OpenAI if not specified

4. **Run the Server**

```bash
python app.py
```

Server runs on `http://localhost:5022`

## 🎯 Testing the API

### Using the Sample UI

The project includes a sample web interface in the `templates` directory that you can use to test the API:

1. Start the server as described above
2. Open your web browser and navigate to `http://localhost:5022`
3. You'll see a user-friendly interface where you can:
   - Upload your resume (PDF format)
   - Enter company name
   - Specify job role
   - Provide job description
   - Select difficulty level
   - Start the interview

The UI will guide you through the entire interview process, showing:
- Company overview
- Interview questions
- Your responses
- Final evaluation

This is the easiest way to test the API's functionality without writing any code.

### Using API Clients

Alternatively, you can test the API using tools like Postman, curl, or any HTTP client. See the API Documentation section below for detailed endpoint information.

## 📚 API Documentation

### Base URL

```
http://localhost:5022
```

### Endpoints

#### 1. Start Interview

Initiates a new interview session with company overview and initial question.

**Endpoint:** `POST /start`

**Content-Type:** `multipart/form-data`

**Request Parameters:**

- `resume`: PDF file containing candidate's resume (required)
- `company_name`: Name of the company (required)
- `job_role`: Position being interviewed for (required)
- `job_description`: Detailed job description (required)
- `difficulty`: Interview difficulty level (optional, defaults to "easy")

**Form Data Example:**
```
resume: [PDF file]
company_name: AIM Media
job_role: AI ML Engineer
job_description: Detailed job description...
difficulty: medium
```

**Using curl:**
```bash
curl -X POST http://localhost:5022/start \
  -F "resume=@/path/to/your/resume.pdf" \
  -F "company_name=AIM Media" \
  -F "job_role=AI ML Engineer" \
  -F "job_description=Detailed job description..." \
  -F "difficulty=medium"
```

**Using Postman:**
1. Select POST method
2. Enter URL: `http://localhost:5022/start`
3. Select "form-data" in the Body tab
4. Add the following key-value pairs:
   - Key: `resume` (Type: File) - Select your PDF file
   - Key: `company_name` (Type: Text) - Enter company name
   - Key: `job_role` (Type: Text) - Enter job role
   - Key: `job_description` (Type: Text) - Enter job description
   - Key: `difficulty` (Type: Text) - Enter difficulty level (optional)

**Success Response (200 OK):**

```json
{
    "company_overview": "Company overview text...",
    "question": "First interview question",
    "state": "introduction",
    "context": [
        {
            "role": "interviewer",
            "message": "Company overview...",
            "state": "company_overview"
        },
        {
            "role": "interviewer",
            "message": "First question...",
            "state": "introduction"
        }
    ]
}
```

**Error Responses:**

- `400 Bad Request`: Missing or invalid parameters
- `500 Internal Server Error`: Server-side processing error

#### 2. Submit Response

Process candidate's response and continue the interview.

**Endpoint:** `POST /respond`

**Content-Type:** `application/json`

**Request Body:**

```json
{
    "response": "Candidate's answer",
    "end_interview": false  // optional, defaults to false
}
```

**Success Response (200 OK):**

```json
{
    "message": "Next question or interview completion message",
    "state": "current_state"
}
```

**Interview Completion Response:**

```json
{
    "status": "completed",
    "message": "Interview completed. Thank you for participating!",
    "state": "closing"
}
```

**Error Responses:**

- `400 Bad Request`: Invalid request format
- `500 Internal Server Error`: Server-side processing error

#### 3. Get Interview Context

Retrieve the complete interview conversation history.

**Endpoint:** `GET /context`

**Success Response (200 OK):**

```json
[
    {
        "role": "interviewer",
        "message": "Message content",
        "state": "state_name"
    },
    {
        "role": "candidate",
        "message": "Response content",
        "state": "state_name"
    }
]
```

#### 4. Get Evaluation

Retrieve the interview evaluation after completion.

**Endpoint:** `GET /evaluation`

**Success Response (200 OK):**

```json
{
    "evaluation": "Detailed interview evaluation text"
}
```

**Error Response (404 Not Found):**

```json
{
    "error": "Evaluation not available yet"
}
```

### Interview States

The interview progresses through the following states:

1. **Company Overview**
   - Introduction and company information
   - Not included in final evaluation
2. **Introduction**
   - Candidate background and experience
   - Focus on professional journey and motivation
3. **Resume Overview**
   - Detailed discussion of qualifications
   - Experience and achievements
4. **Technical Evaluation**
   - Technical skills assessment
   - Problem-solving abilities
5. **Behavioral Assessment**
   - Soft skills evaluation
   - Past behavior analysis
6. **Cultural Fit**
   - Values alignment
   - Work style compatibility
7. **Closing**
   - Final questions
   - Interview wrap-up

### Difficulty Levels

- **Easy**: 1 question per state
- **Medium**: 2 questions per state
- **Hard**: 3 questions per state

### Error Handling

All endpoints follow a consistent error response format:

```json
{
    "error": "Error message description"
}
```

Common error scenarios:

- Missing or invalid API keys
- Invalid file formats
- Server processing errors
- Invalid request parameters

## 📁 Project Structure

```
.
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env                  # Environment variables (API keys)
├── .gitignore           # Git ignore rules
├── interview_log.json    # Interview conversation logs
├── interview_evaluation.txt  # Final interview evaluation
└── templates/           # Frontend templates
    └── index.html      # Main interview interface
```