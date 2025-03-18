import os
import json
from flask import Flask, request, jsonify
from transitions import Machine
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from dotenv import load_dotenv


load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

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
        'introduction',
        'resume_overview',
        'technical_evaluation',
        'behavioral_assessment',
        'cultural_fit',
        'closing'
    ]

    def __init__(self):
        self.machine = Machine(model=self, states=InterviewStateMachine.states, initial='introduction')
        self.machine.add_transition('next_state', 'introduction', 'resume_overview')
        self.machine.add_transition('next_state', 'resume_overview', 'technical_evaluation')
        self.machine.add_transition('next_state', 'technical_evaluation', 'behavioral_assessment')
        self.machine.add_transition('next_state', 'behavioral_assessment', 'cultural_fit')
        self.machine.add_transition('next_state', 'cultural_fit', 'closing')

        self.mode = 'questioning'
        self.step_count = 0
        self.max_steps = 2

# Initialize state machine
interview = InterviewStateMachine()
context = []  # Store conversation history

# Initialize Flask app
app = Flask(__name__)

# === LLM Functions ===
def generate_question(state):
    prompt = f"""
    You are an experienced interviewer conducting a structured interview.
    
    Current state: {state}
    Context so far: {context}
    Generate a professional question for this state.
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
    context.append({"candidate": response})
    
    if is_question(response):
        # Candidate is asking a question → Answer it
        interview.mode = 'answering'
        answer = generate_response(response)
        context.append({"interviewer": answer})
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
    context.append({"interviewer": next_question})
    return next_question

def generate_response(question):
    prompt = f"""
    You are an experienced interviewer.
    Candidate's question: {question}
    Provide a helpful and professional response.
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
    prompt = f"""
    You are an expert interviewer evaluating a candidate's interview performance.
    
    Below is the full conversation between the interviewer and the candidate:
    
    {context}
    
    Evaluate the candidate's performance based on the following criteria:
    - **Introduction:** Clarity and confidence in introducing themselves.
    - **Resume Overview:** Relevance of experience and ability to explain past work.
    - **Technical Evaluation:** Depth of technical knowledge and problem-solving.
    - **Behavioral Assessment:** Ability to communicate, teamwork, and leadership.
    - **Cultural Fit:** Alignment with company values and motivation.

    Provide a brief summary and a score (out of 10) for each category.
    """
    
    response = conversation.run(prompt).strip()
    print(f"Evaluation: {response}")
    
    # Save the evaluation to a file
    with open('interview_evaluation.txt', 'w') as f:
        f.write(response)
    
    return response

# === Flask Routes ===
@app.route('/start', methods=['GET'])
def start_interview():
    interview.state = 'introduction'
    interview.step_count = 0
    context.clear()
    memory.clear()
    
    question = generate_question(interview.state)
    context.append({"interviewer": question})
    return jsonify({'question': question})

@app.route('/respond', methods=['POST'])
def respond():
    data = request.json
    response = data.get('response')
    
    if not response:
        return jsonify({'error': 'Response is required'}), 400
    
    next_message = handle_response(response)
    
    if interview.state == 'closing':
        return jsonify({
            'status': 'completed', 
            'message': next_message
        })
    
    return jsonify({'message': next_message})

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
    app.run(debug=True)
