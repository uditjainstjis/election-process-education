import os
import logging
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configure Gemini AI
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None
    logger.warning('GEMINI_API_KEY not set. AI features will be limited.')

ELECTION_SYSTEM_PROMPT = """
You are ElectionBot, an expert AI assistant specialized in educating citizens about 
the election process in India and globally. Your role is to:

1. Explain how elections work - registration, voting procedures, counting
2. Clarify voter rights and responsibilities
3. Describe the role of Election Commission of India (ECI)
4. Explain different types of elections (Lok Sabha, Rajya Sabha, State Legislative Assembly, Local Body)
5. Guide users on voter registration (Form 6), checking voter ID status
6. Explain Electronic Voting Machines (EVM) and VVPAT systems
7. Address electoral misconduct and how to report it
8. Explain the Model Code of Conduct
9. Share information about NOTA (None of the Above) option
10. Explain reservation in elections (SC/ST seats)

Always be:
- Factual and unbiased
- Clear and simple (accessible to first-time voters)
- Supportive of democratic values
- Ready to answer in Hindi if asked

Do NOT promote any political party or candidate.
"""


@app.route('/')
def index():
    """Main page - Election Education Hub."""
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    """Handle AI chat requests about elections."""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'No message provided'}), 400

        user_message = data['message'].strip()
        if not user_message:
            return jsonify({'error': 'Empty message'}), 400

        if len(user_message) > 1000:
            return jsonify({'error': 'Message too long (max 1000 characters)'}), 400

        if not model:
            return jsonify({
                'response': get_static_response(user_message),
                'source': 'static'
            })

        full_prompt = f"{ELECTION_SYSTEM_PROMPT}\n\nUser Question: {user_message}\n\nProvide a helpful, accurate response:"
        response = model.generate_content(full_prompt)
        return jsonify({
            'response': response.text,
            'source': 'gemini'
        })

    except Exception as e:
        logger.error(f'Chat error: {e}')
        return jsonify({'error': 'Failed to process request. Please try again.'}), 500


@app.route('/quiz', methods=['GET'])
def quiz():
    """Get a quiz question about elections."""
    try:
        if not model:
            return jsonify({'questions': get_static_quiz()})

        prompt = """
Generate 5 multiple-choice quiz questions about the Indian election process.
Return as JSON array with format:
[
  {
    "question": "Question text",
    "options": ["A. Option1", "B. Option2", "C. Option3", "D. Option4"],
    "answer": "A",
    "explanation": "Brief explanation"
  }
]
Topics: voter registration, EVM, Election Commission, voting procedure, electoral rolls.
Only return valid JSON, no markdown.
"""
        response = model.generate_content(prompt)
        import json
        text = response.text.strip()
        if text.startswith('```'):
            text = text.split('\n', 1)[1].rsplit('```', 1)[0]
        questions = json.loads(text)
        return jsonify({'questions': questions})

    except Exception as e:
        logger.error(f'Quiz error: {e}')
        return jsonify({'questions': get_static_quiz()})


@app.route('/health')
def health():
    """Health check endpoint for Cloud Run."""
    return jsonify({'status': 'healthy', 'service': 'election-education-hub'})


def get_static_response(message):
    """Fallback static responses when AI is not available."""
    message_lower = message.lower()
    if 'register' in message_lower or 'registration' in message_lower:
        return "To register as a voter in India, you must be 18+ years old and an Indian citizen. Fill Form 6 on the National Voters' Service Portal (voters.eci.gov.in) or visit your nearest Electoral Registration Officer. You'll need Aadhaar, age proof, and address proof."
    elif 'evm' in message_lower or 'voting machine' in message_lower:
        return "Electronic Voting Machines (EVMs) are tamper-proof standalone devices used in Indian elections since 1999. They consist of a Control Unit (with the Presiding Officer) and Ballot Unit (where voters press buttons). VVPAT (Voter Verifiable Paper Audit Trail) provides a paper slip showing your vote for 7 seconds for verification."
    elif 'nota' in message_lower:
        return "NOTA (None of the Above) is an option on Indian EVMs introduced in 2013 by the Supreme Court order. It allows voters to reject all candidates. NOTA votes are counted but don't affect the result - the candidate with the most votes still wins."
    elif 'commission' in message_lower or 'eci' in message_lower:
        return "The Election Commission of India (ECI) is an autonomous constitutional authority established in 1950. It supervises and controls all elections to Parliament, State Legislatures, the office of the President and Vice-President. The Chief Election Commissioner heads it."
    else:
        return "Welcome to the Election Education Hub! I can help you with: voter registration, how to vote, understanding EVMs, election types in India, voter rights, and more. Please ask a specific question!"


def get_static_quiz():
    """Static quiz questions as fallback."""
    return [
        {
            "question": "At what age can an Indian citizen register to vote?",
            "options": ["A. 16 years", "B. 18 years", "C. 21 years", "D. 25 years"],
            "answer": "B",
            "explanation": "Indian citizens who are 18 years or older on January 1st of the qualifying year are eligible to register as voters."
        },
        {
            "question": "What does NOTA stand for in Indian elections?",
            "options": ["A. None of the Applicants", "B. None of the Above", "C. Not of the Area", "D. National Option to Abstain"],
            "answer": "B",
            "explanation": "NOTA stands for None of the Above. It was introduced in 2013 following a Supreme Court order to allow voters to reject all candidates."
        },
        {
            "question": "Which form is used for new voter registration in India?",
            "options": ["A. Form 4", "B. Form 5", "C. Form 6", "D. Form 8"],
            "answer": "C",
            "explanation": "Form 6 is used for new voter registration. Form 8 is used for corrections, and Form 7 is for deletion from electoral rolls."
        },
        {
            "question": "What is VVPAT?",
            "options": ["A. Voter Verified Paper Audit Trail", "B. Voter Verifiable Paper Audit Trail", "C. Verified Voting Paper and Tally", "D. Verified Voter Paper and Track"],
            "answer": "B",
            "explanation": "VVPAT (Voter Verifiable Paper Audit Trail) is a system that provides voters with feedback that their vote was cast correctly by showing a paper slip for 7 seconds."
        },
        {
            "question": "How many Lok Sabha constituencies are there in India?",
            "options": ["A. 442", "B. 530", "C. 543", "D. 545"],
            "answer": "C",
            "explanation": "There are 543 Lok Sabha constituencies in India. Elections are held every 5 years unless dissolved earlier."
        }
    ]


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
