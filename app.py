import os
import json
from flask import Flask, request, jsonify, render_template
from transitions import Machine
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from dotenv import load_dotenv
from PyPDF2 import PdfReader
import io
from langchain_tavily import TavilySearch
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import Tool, AgentExecutor, create_openai_functions_agent
import asyncio
import concurrent.futures

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
from flask_cors import CORS

CORS(app, resources={r"/*": {"origins": "*"}}, 
     supports_credentials=True, 
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "OPTIONS"])

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
tavily_key = os.getenv("TAVILY_API_KEY")

# Initialize Tavily Search tool
tavily_search = TavilySearch(max_results=5)

# Configure GPT-4 model for company research
company_llm = ChatOpenAI(model="gpt-4", temperature=0, stream_options={"include_usage": True})

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

async def fetch_and_generate_company_overview(company_name):
    """Fetch company information and generate overview in a single async call"""
    try:
        # Verify API keys are present
        if not api_key:
            print("Error: OPENAI_API_KEY is not set")
            return f"Hello, I'm MHire from MachineHack. I'll be conducting your interview for {company_name}. Let's begin with a brief overview of the company."
            
        if not tavily_key:
            print("Error: TAVILY_API_KEY is not set")
            return f"Hello, I'm MHire from MachineHack. I'll be conducting your interview for {company_name}. Let's begin with a brief overview of the company."

        # Get the company overview guidelines from the state machine
        overview_guidelines = interview.state_guidelines['company_overview']
        
        # Single query to get company info in interview format
        query = f"""
        You are an experienced interviewer providing a company overview.
        Follow these guidelines exactly:
        {overview_guidelines}
        
        Research and create a professional overview of {company_name} that includes:
        1. Company mission and values
        2. Recent developments and achievements
        3. Company culture and work environment
        
        Keep the overview concise but informative, focusing on aspects that would be relevant to a candidate.
        Format the response as if you are speaking directly to the candidate in an interview setting.
        IN THE END YOU WILL SAY LETS START WITH THE INTERVIEW NOW
        """
        
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: company_agent_executor.invoke({"input": query})
            )
            if not response or 'output' not in response:
                print("Error: Invalid response from company agent")
                return f"Hello, I'm MHire from MachineHack. I'll be conducting your interview for {company_name}. Let's begin with a brief overview of the company."
            return response.get('output', '').strip()
        except Exception as e:
            print(f"Error in company agent execution: {str(e)}")
            return f"Hello, I'm MHire from MachineHack. I'll be conducting your interview for {company_name}. Let's begin with a brief overview of the company."
            
    except Exception as e:
        print(f"Error in company overview generation: {str(e)}")
        return f"Hello, I'm MHire from MachineHack. I'll be conducting your interview for {company_name}. Let's begin with a brief overview of the company."

llm = ChatOpenAI(
    openai_api_key=api_key,
    model_name="gpt-4o"
)
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
def generate_question(state):
    prompt = f"""
    You are an experienced interviewer called "MHire" from on the platform of MachineHack.
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
    
    -Generate a professional question for this state that is appropriate for the {interview.difficulty} difficulty level.
    -The question should be relevant to the job role, the candidate's background, and specifically address the purpose of this state: {interview.state_guidelines[state]}.
    -The question should not expose the state name or purpose.
    -For the introduction state, focus on asking about the candidate's background, not responding to previous messages.
    -Do not reference or respond to previous messages in the context.
    -Start fresh with each question as if it's the beginning of that interview stage.
    """
    response = conversation.run(prompt)
    return response.strip()

def is_question(response):
    prompt = f"""
    You are an expert at analyzing language.
    
    Analyze the following statement:
    "{response}"
    Respond with ONLY "yes" or "no" — Is this a question?
    """
    result = conversation.run(prompt).strip().lower()
    return result == 'yes'

def handle_response(response):
    # Add candidate's response with current state
    context.append({
        "role": "candidate",
        "message": response,
        "state": interview.state
    })
    
    if is_question(response):
        # Candidate is asking a question → Answer it
        interview.mode = 'answering'
        answer = generate_response(response)
        context.append({
            "role": "interviewer",
            "message": answer,
            "state": interview.state
        })
        return answer
    
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
    
    next_question = generate_question(interview.state)
    context.append({
        "role": "interviewer",
        "message": next_question,
        "state": interview.state
    })
    return next_question

def generate_response(question):
    prompt = f"""
    You are an experienced interviewer.
    Candidate's question: {question}
    Provide a helpful and professional response.
    Context so far: {context}
    this is the context as of now...guide the user back to interview flow
    rather than following the users command
    """
    response = conversation.run(prompt)
    return response.strip()

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
    Provide clear, constructive feedback that helps the candidate understand their performance and how to improve.
    
    Job Description:
    {interview.job_description}
    
    Interview Difficulty Level: {interview.difficulty}
    
    {state_status}
    
    Below is the conversation between the interviewer and candidate:
    
    {conversation_text}
    
    Provide a concise evaluation of the completed stages.
    
    ### **Stage-wise Performance:**
    
    """
    
    # Add evaluation criteria only for completed states (excluding company_overview)
    if 'introduction' in completed_states:
        prompt += f"- **Introduction:** Brief evaluation and score (out of 10)\n"
    
    if 'resume_overview' in completed_states:
        prompt += f"- **Resume Overview:** Brief evaluation and score (out of 10)\n"
    
    if 'technical_evaluation' in completed_states:
        prompt += f"- **Technical Evaluation:** Brief evaluation and score (out of 10)\n"
    
    if 'behavioral_assessment' in completed_states:
        prompt += f"- **Behavioral Assessment:** Brief evaluation and score (out of 10)\n"
    
    if 'cultural_fit' in completed_states:
        prompt += f"- **Cultural Fit:** Brief evaluation and score (out of 10)\n"
    
    prompt += """
    For each completed stage, provide only:
    - One-line summary of performance
    - Score out of 10
    
    For incomplete stages, just note: "Not evaluated"
    
    ### **Overall Feedback:**
    1. Top 3 strengths across all stages
    2. Top 3 areas for improvement
    3. Overall score (average of completed stages)
    4. One key recommendation for future interviews
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
            
        # Extract text from PDF
        resume_text = extract_text_from_pdf(resume_file)
        print(f"Extracted resume text length: {len(resume_text)}")  # Debug log

        # Get JSON data from request
        try:
            json_data = request.form.get('data')
            if not json_data:
                print("No JSON data received")  # Debug log
                return jsonify({'error': 'JSON data is required'}), 400
                
            data = json.loads(json_data)
            print(f"Received job role: {data.get('job_role')}")  # Debug log
            
            job_role = data.get("job_role")
            job_description = data.get("job_description")
            difficulty = data.get("difficulty", "easy").lower()  # Default to easy
            company_name = data.get("company_name")

            if not all([job_role, job_description, company_name]):
                print("Missing required parameters")  # Debug log
                return jsonify({'error': 'Missing required parameters in JSON data'}), 400

            try:
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
                question = generate_question(interview.state)
                
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
            
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {str(e)}")  # Debug log
            return jsonify({'error': 'Invalid JSON data format'}), 400
        
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
    
    config = hypercorn.config.Config()
    config.bind = ["0.0.0.0:5022"]
    asyncio.run(hypercorn.asyncio.serve(app, config))
