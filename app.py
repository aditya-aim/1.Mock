import os
import json
from flask import Flask, request, jsonify, render_template
from transitions import Machine
from langchain_community.chat_models import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_community.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from dotenv import load_dotenv
from PyPDF2 import PdfReader
import io
from langchain_tavily import TavilySearch
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import Tool, AgentExecutor, create_openai_functions_agent
import asyncio
import concurrent.futures
import datetime

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
from flask_cors import CORS

CORS(app, resources={r"/*": {"origins": "*"}}, 
     supports_credentials=True, 
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "OPTIONS"])

load_dotenv()

# API Keys
api_key = os.getenv("OPENAI_API_KEY")
tavily_key = os.getenv("TAVILY_API_KEY")
groq_key = os.getenv("GROQ_API_KEY")
nebius_key = os.getenv("NEBIUS_API_KEY")

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()  # groq, nebius, openai   (default: groq) 
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")  # groq: llama-3.3-70b-versatile, openai: gpt-4, nebius: meta-llama/Meta-Llama-3.1-70B-Instruct-fast

def get_llm():
    """Get the configured LLM based on environment settings"""
    if LLM_PROVIDER == "groq":
        if not groq_key:
            raise ValueError("GROQ_API_KEY is required when using Groq as LLM provider")
        return ChatGroq(
            groq_api_key=groq_key,
            model_name=LLM_MODEL,
            temperature=0,
            max_tokens=4096
        )
    elif LLM_PROVIDER == "nebius":
        if not nebius_key:
            raise ValueError("NEBIUS_API_KEY is required when using Nebius as LLM provider")
        return ChatOpenAI(
            openai_api_key=nebius_key,
            model_name=LLM_MODEL,
            temperature=0,
            max_tokens=4096,
            base_url="https://api.studio.nebius.com/v1/",
            extra_body={
                "top_k": 50,
                "top_p": 0.9
            }
        )
    else:  # Default to OpenAI
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required when using OpenAI as LLM provider")
        return ChatOpenAI(
            openai_api_key=api_key,
            model_name=LLM_MODEL,
            temperature=0,
            max_tokens=4096
        )

# Initialize Tavily Search tool
tavily_search = TavilySearch(max_results=5)

# Configure LLM for company research
company_llm = get_llm()

# Define prompt template for company research
company_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a knowledgeable assistant providing real-time information about companies."),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# Define tools for company research
company_tools = [
    Tool(
        name="TavilySearch",
        func=tavily_search.run,
        description="Retrieves real-time information from the web.",
    ),
]

# Create agent and executor for company research
company_agent = create_openai_functions_agent(company_llm, company_tools, company_prompt)
company_agent_executor = AgentExecutor(agent=company_agent, tools=company_tools, verbose=True)

# Initialize main LLM for interview
llm = get_llm()

# Initialize Conversation Memory
memory = ConversationBufferMemory()
conversation = ConversationChain(llm=llm, memory=memory, verbose=True)

# Define Interview State Machine
class InterviewStateMachine:
    states = [
        'company_overview',
        'introduction',
        'resume_overview',
        'technical_evaluation',
        'behavioral_assessment',
        'cultural_fit',
        'closing'
    ]

    state_guidelines = {
        'company_overview': """You should greet the candidate by their name, introduce yourself with your name(MHire),
        mention your platform name(MachineHack), and the company for which you are interviewing the candidate
        and then Provide a comprehensive overview of the company, its mission, values, and recent developments.
        This should be based on real-time data fetched about the company.""",

        'introduction': """Focus on getting to know the candidate's background question the candidate to share their story for this role.""",
        'resume_overview': 'Detailed discussion of candidate\'s experience and qualifications',
        'technical_evaluation': 'Assessment of technical skills and problem-solving abilities',
        'behavioral_assessment': 'Evaluation of soft skills and past behavior in work situations',
        'cultural_fit': 'Understanding candidate\'s values and alignment with company culture',
        'closing': 'Final questions and interview wrap-up'
    }

    def __init__(self):
        self.machine = Machine(model=self, states=InterviewStateMachine.states, initial='company_overview')
        self.machine.add_transition('next_state', 'company_overview', 'introduction')
        self.machine.add_transition('next_state', 'introduction', 'resume_overview')
        self.machine.add_transition('next_state', 'resume_overview', 'technical_evaluation')
        self.machine.add_transition('next_state', 'technical_evaluation', 'behavioral_assessment')
        self.machine.add_transition('next_state', 'behavioral_assessment', 'cultural_fit')
        self.machine.add_transition('next_state', 'cultural_fit', 'closing')

        self.mode = 'questioning'
        self.step_count = 0
        self.max_steps = 1  # Default to easy mode
        self.job_role = None
        self.resume = None
        self.job_description = None
        self.difficulty = "easy"
        self.company_name = None
        self.company_info = None

    def set_interview_details(self, job_role, resume, job_description, difficulty, company_name):
        self.job_role = job_role
        self.resume = resume
        self.job_description = job_description
        self.difficulty = difficulty.lower() if difficulty in ["easy", "medium", "hard"] else "easy"
        self.company_name = company_name
        # Set max_steps based on difficulty
        self.max_steps = {
            "easy": 1,
            "medium": 2,
            "hard": 3
        }.get(self.difficulty, 1)

# Initialize state machine
interview = InterviewStateMachine()
context = []  # Store conversation history

# === LLM Functions ===
def generate_question(state, candidate_response):
    prompt = f"""
    You are an experienced interviewer called "MHire" from the platform of MachineHack.
    You are conducting a structured interview for the company whose job description is given below.
    Job Description:
    {interview.job_description}
    You are conducting a structured interview for the position of {interview.job_role}.
    
    Candidate's Resume:
    {interview.resume}
    
    Interview Difficulty Level: {interview.difficulty}
    Current state: {state}
    State Purpose: {interview.state_guidelines[state]}
    Context so far: {context}
    Candidate's response: {candidate_response}
    
    Your task:
    1. If the candidate's response is a question:
       - Acknowledge their question briefly
       - Provide a concise, relevant answer
       - Transition back to the interview by asking your next question
    2. If the candidate's response is not a question:
       - First, acknowledge and briefly reflect on the candidate's previous response
       - Then, generate the next interview question that:
         * Builds upon their previous response
         * Is appropriate for the current difficulty level
         * Is relevant to the job role and candidate's background
         * Addresses the purpose of the current state without exposing the state name
         * For introduction state, focuses on candidate's background
         * Maintains conversation flow while exploring new aspects
       - Do not reference messages beyond the immediate context
       - Keep the transition natural and professional
    
    Remember to maintain a professional tone and guide the interview flow appropriately.
    """
    
    response = conversation.run(prompt)
    return response.strip()

def handle_response(response):
    # Add candidate's response with current state
    context.append({
        "role": "candidate",
        "message": response,
        "state": interview.state
    })
    
    interview.mode = 'questioning'
    interview.step_count += 1
    
    if interview.step_count >= interview.max_steps:
        interview.step_count = 0
        if interview.state != 'closing':
            interview.next_state()
    
    if interview.state == 'closing':
        save_chat_log()
        evaluation = evaluate_conversation()
        return f"Interview completed. Thank you for participating!\n\n{evaluation}"
    
    next_question = generate_question(interview.state, response)
    context.append({
        "role": "interviewer",
        "message": next_question,
        "state": interview.state
    })
    return next_question

# === New Functions ===
def save_chat_log():
    file_path = 'interview_log.json'
    with open(file_path, 'w') as f:
        json.dump(context, f, indent=4)
    print(f"Chat log saved to {file_path}")

def evaluate_conversation():
    # Format the conversation for evaluation
    formatted_conversation = []
    completed_states = set()
    
    for entry in context:
        # Skip company_overview state from evaluation
        if entry['state'] != 'company_overview':
            formatted_conversation.append(f"[{entry['state'].upper()}] {entry['role'].title()}: {entry['message']}")
            completed_states.add(entry['state'])
    
    conversation_text = "\n".join(formatted_conversation)
    
    # Get all possible states and identify incomplete ones (excluding company_overview)
    all_states = set(state for state in interview.states if state != 'company_overview')
    incomplete_states = all_states - completed_states
    
    # Create state status summary
    state_status = "\n### Interview Progress:\n"
    for state in interview.states:
        if state != 'company_overview':  # Skip company_overview from status
            status = "✅ Completed" if state in completed_states else "⏳ Not Reached"
            state_status += f"- **{state.upper()}**: {status}\n"
    
    prompt = f"""
    You are an experienced interviewer evaluating a candidate's performance for the position of {interview.job_role}.
    Provide a structured, insightful, and actionable evaluation following the format below.

    Job Description:
    {interview.job_description}

    Interview Difficulty Level: {interview.difficulty}

    {state_status}

    Below is the conversation between the interviewer and candidate:

    {conversation_text}

    ### **Candidate Summary**
    - **Job Role:** {interview.job_role}
    - **Total Score:** (Average of completed stages)
    - **Interview Status:** (Ready / Needs Improvement / Not Ready)

    ### **Stage-wise Performance**
    Provide a brief yet insightful evaluation for each completed stage:
    """
    if 'introduction' in completed_states:
        prompt += "- **Introduction:** Summary of performance, key impressions, score (out of 10)\n"
    if 'resume_overview' in completed_states:
        prompt += "- **Resume Overview:** Depth of experience, clarity of responses, score (out of 10)\n"
    if 'technical_evaluation' in completed_states:
        prompt += "- **Technical Evaluation:** Problem-solving skills, technical knowledge, score (out of 10)\n"
    if 'behavioral_assessment' in completed_states:
        prompt += "- **Behavioral Assessment:** Communication, adaptability, score (out of 10)\n"
    if 'cultural_fit' in completed_states:
        prompt += "- **Cultural Fit:** Alignment with company values, attitude, score (out of 10)\n"

    prompt += """
    For incomplete stages, note: "Not evaluated"

    ### **Overall Evaluation**
    1. **Top 3 Strengths:** Based on completed stages
    2. **Top 3 Areas for Improvement:** With context and suggestions
    3. **Readiness Flag:** (Strong / Moderate / Weak)
    4. **Overall Score:** (Average of completed stage scores)

    ### **Feedback & Resources**
    - Actionable improvement tips tailored to the candidate
    - Relevant learning resources or study materials

    ### **Final Comments**
    Provide an encouraging conclusion with a motivational note for the candidate.

    ---
    Ensure that your feedback is constructive, balanced, and supportive, helping the candidate grow and refine their skills.
    """

    response = conversation.run(prompt).strip()
    print(f"Evaluation: {response}")

    # Save the evaluation to a file
    with open('interview_evaluation.txt', 'w') as f:
        f.write(response)

    return response


def extract_text_from_pdf(pdf_file):
    """
    Extract text from a PDF file with robust error handling
    """
    try:
        print(f"Processing PDF file: {pdf_file.filename}")  # Debug log
        
        # Create a copy of the file in memory to prevent EOF issues
        pdf_content = pdf_file.read()
        print(f"Read {len(pdf_content)} bytes from PDF")  # Debug log
        
        pdf_file_copy = io.BytesIO(pdf_content)
        
        try:
            # Try to read with default settings
            pdf_reader = PdfReader(pdf_file_copy, strict=False)
            print(f"Successfully created PDF reader with {len(pdf_reader.pages)} pages")  # Debug log
        except Exception as e:
            print(f"Failed first attempt to read PDF: {str(e)}")  # Debug log
            # If failed, try again with the original file and strict mode off
            pdf_file.seek(0)  # Reset file pointer
            pdf_reader = PdfReader(pdf_file, strict=False)
            print("Successfully created PDF reader on second attempt")  # Debug log
        
        # Extract text from all pages
        text = ""
        for i, page in enumerate(pdf_reader.pages):
            try:
                page_text = page.extract_text()
                text += page_text + "\n"
                print(f"Successfully extracted text from page {i+1}")  # Debug log
            except Exception as e:
                print(f"Failed to extract text from page {i+1}: {str(e)}")  # Debug log
                text += f"[Content extraction failed for page {i+1}]\n"
        
        if not text.strip():
            print("No text content extracted from PDF")  # Debug log
            return "Unable to extract text from the PDF. Please ensure the PDF contains readable text."
        
        print(f"Successfully extracted {len(text)} characters of text")  # Debug log    
        return text.strip()
    except Exception as e:
        print(f"PDF Processing Error: {str(e)}")  # Debug log
        return f"Error processing the PDF file: {str(e)}"

# === Flask Routes ===
@app.route('/')
def index():
    return render_template('index.html')

async def check_llm_availability():
    """Check availability of all configured LLM providers"""
    llm_status = {}
    
    # Check OpenAI
    if api_key:
        try:
            test_llm = ChatOpenAI(
                openai_api_key=api_key,
                model_name="gpt-3.5-turbo",
                temperature=0,
                max_tokens=10
            )
            test_llm.invoke("test")
            llm_status["openai"] = {"status": "up", "model": "gpt-3.5-turbo"}
        except Exception as e:
            llm_status["openai"] = {"status": "down", "error": str(e)}
    
    # Check Groq
    if groq_key:
        try:
            test_llm = ChatGroq(
                groq_api_key=groq_key,
                model_name=LLM_MODEL,
                temperature=0,
                max_tokens=10
            )
            test_llm.invoke("test")
            llm_status["groq"] = {
                "status": "up",
                "model": LLM_MODEL,
                "configured_model": LLM_MODEL if LLM_PROVIDER == "groq" else None
            }
        except Exception as e:
            llm_status["groq"] = {"status": "down", "error": str(e)}
    
    # Check Nebius
    if nebius_key:
        try:
            test_llm = ChatOpenAI(
                openai_api_key=nebius_key,
                model_name="meta-llama/Meta-Llama-3.1-70B-Instruct-fast",
                temperature=0,
                max_tokens=10,
                base_url="https://api.studio.nebius.com/v1/"
            )
            test_llm.invoke("test")
            llm_status["nebius"] = {"status": "up", "model": "meta-llama/Meta-Llama-3.1-70B-Instruct-fast"}
        except Exception as e:
            llm_status["nebius"] = {"status": "down", "error": str(e)}
    
    return llm_status

@app.route('/ping', methods=['GET'])
async def ping():
    """Health check endpoint that verifies server status and LLM configuration"""
    try:
        # Check if LLM provider is configured
        provider_status = {
            "provider": LLM_PROVIDER,
            "model": LLM_MODEL,
            "status": "configured"
        }
        
        # Check API keys based on provider
        if LLM_PROVIDER == "groq" and not groq_key:
            provider_status["status"] = "error"
            provider_status["message"] = "GROQ_API_KEY is missing"
        elif LLM_PROVIDER == "nebius" and not nebius_key:
            provider_status["status"] = "error"
            provider_status["message"] = "NEBIUS_API_KEY is missing"
        elif LLM_PROVIDER == "openai" and not api_key:
            provider_status["status"] = "error"
            provider_status["message"] = "OPENAI_API_KEY is missing"
        
        # Check availability of all LLMs
        llm_status = await check_llm_availability()
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.datetime.now().isoformat(),
            "llm": provider_status,
            "tavily": "configured" if tavily_key else "missing",
            "llm_providers": llm_status
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.datetime.now().isoformat()
        }), 500

@app.route('/start', methods=['POST'])
async def start_interview():
    try:
        print("Received interview start request")  # Debug log
        
        # Handle PDF resume upload
        if 'resume' not in request.files:
            print("No resume file in request")  # Debug log
            return jsonify({'error': 'Resume PDF file is required'}), 400
            
        resume_file = request.files['resume']
        print(f"Resume file received: {resume_file.filename}")  # Debug log
        
        if resume_file.filename == '':
            print("Empty filename received")  # Debug log
            return jsonify({'error': 'No selected file'}), 400
            
        if not resume_file.filename.endswith('.pdf'):
            print("Invalid file type received")  # Debug log
            return jsonify({'error': 'File must be a PDF'}), 400

        # Get form data
        company_name = request.form.get('company_name')
        job_role = request.form.get('job_role')
        job_description = request.form.get('job_description')
        difficulty = request.form.get('difficulty', 'easy').lower()

        if not all([company_name, job_role, job_description]):
            print("Missing required parameters")  # Debug log
            return jsonify({'error': 'Missing required parameters'}), 400

        try:
            # Extract text from PDF
            resume_text = extract_text_from_pdf(resume_file)
            print(f"Extracted resume text length: {len(resume_text)}")  # Debug log

            # Set interview details
            interview.state = 'company_overview'
            interview.step_count = 0
            interview.set_interview_details(job_role, resume_text, job_description, difficulty, company_name)
            context.clear()
            memory.clear()

            # Generate company overview
            try:
                company_overview = await fetch_and_generate_company_overview(company_name)
            except Exception as e:
                print(f"Error generating company overview: {str(e)}")
                company_overview = f"Hello, I'm MHire from MachineHack. I'll be conducting your interview for {company_name}. Let's begin with a brief overview of the company."
            
            # Add company overview to context
            context.append({
                "role": "interviewer",
                "message": company_overview,
                "state": "company_overview"
            })

            # Generate first question for introduction state
            interview.next_state()  # Move to introduction state
            question = generate_question(interview.state, "")
            
            # Add the first question to context BEFORE returning
            context.append({
                "role": "interviewer",
                "message": question,
                "state": interview.state
            })
            
            # Return both messages to the frontend
            return jsonify({
                'company_overview': company_overview,
                'question': question,
                'state': interview.state,
                'context': context  # Include the full context
            })
            
        except Exception as e:
            print(f"Error during interview setup: {str(e)}")  # Debug log
            return jsonify({'error': f'Failed to setup interview: {str(e)}'}), 500
            
    except Exception as e:
        print(f"Unexpected error: {str(e)}")  # Debug log
        return jsonify({'error': str(e)}), 500

@app.route('/respond', methods=['POST'])
def respond():
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
            
        data = request.get_json()
        if data is None:
            return jsonify({'error': 'Invalid JSON in request'}), 400
            
        response = data.get('response')
        end_interview = data.get('end_interview', False)
        
        if not response:
            return jsonify({'error': 'Response is required'}), 400
        
        try:
            if end_interview:
                # Force transition to closing state
                while interview.state != 'closing':
                    interview.next_state()
                
                next_message = handle_response(response)
                
                return jsonify({
                    'status': 'completed', 
                    'message': next_message,
                    'state': 'closing'
                })
            
            next_message = handle_response(response)
            
            if interview.state == 'closing':
                return jsonify({
                    'status': 'completed', 
                    'message': next_message,
                    'state': 'closing'
                })
            
            return jsonify({
                'message': next_message,
                'state': interview.state
            })
        except Exception as e:
            print(f"Error processing response: {str(e)}")  # Debug log
            return jsonify({'error': f'Failed to process response: {str(e)}'}), 500
            
    except Exception as e:
        print(f"Unexpected error in respond route: {str(e)}")  # Debug log
        return jsonify({'error': str(e)}), 500

@app.route('/context', methods=['GET'])
def get_context():
    return jsonify(context)

@app.route('/evaluation', methods=['GET'])
def get_evaluation():
    try:
        with open('interview_evaluation.txt', 'r') as f:
            evaluation = f.read()
        return jsonify({'evaluation': evaluation})
    except FileNotFoundError:
        return jsonify({'error': 'Evaluation not available yet'}), 404

# === Start Flask App ===
if __name__ == '__main__':
    import hypercorn.asyncio
    import hypercorn.config
    import socket
    
    # Get local IP address
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    config = hypercorn.config.Config()
    config.bind = ["0.0.0.0:5022"]
    
    print("\n🚀 Server is running!")
    print(f"📱 Access the application via:")
    print(f"   Local: http://localhost:5022")
    print(f"   IP:    http://{local_ip}:5022")
    print("\nPress CTRL + C to quit\n")
    
    asyncio.run(hypercorn.asyncio.serve(app, config))
