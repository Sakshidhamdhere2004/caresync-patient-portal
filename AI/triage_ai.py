# FILE: triage_ai.py
# WHO WRITES THIS: Data Analyst
# WHAT THIS FILE DOES:
#   1. build_prompt(patient) - Takes a patient dictionary and creates
#      a clear message (prompt) to send to the Groq AI.
#   2. run_triage(patient) - Sends the prompt to Groq AI and returns
#      the AI's response as a dictionary.
#
# The Analyst does NOT write SQL. They receive a patient dict
# from database.py and work only with the AI prompt and response.
# ============================================================


import os                       # To read the GROQ_API_KEY from .env
from groq import Groq           # The official Groq Python SDK
from dotenv import load_dotenv  # To load the .env file


# Load .env file so os.getenv('GROQ_API_KEY') works
load_dotenv()


# Create the Groq client - this is the object we use to call the AI
# It reads the GROQ_API_KEY automatically from the .env file
client = Groq(api_key=os.getenv('GROQ_API_KEY'))


# The AI model we will use
# llama-3.3-70b-versatile is a powerful, free model on Groq
GROQ_MODEL = 'openai/gpt-oss-20b'




def build_prompt(patient: dict) -> str:
    """
    DATA ANALYST FUNCTION: Builds the prompt (question) to send to the AI.


    A well-written prompt gives a better AI response.
    This function formats the patient's data into a structured message.


    Parameters:
        patient (dict): A patient record received from database.py
    Returns:
        A string - the complete message to send to Groq AI
    """


    # We use an f-string to fill in the patient's actual values
    # patient['name'] will become 'Priya Sharma', patient['age'] will become 28, etc.
    # .get() is used for optional fields - if bp is not recorded, it shows 'Not recorded'
    prompt = f"""
You are a medical triage assistant helping a nurse at a hospital outpatient department in India.
A patient has arrived. Based on the information below, provide a brief triage assessment.


Patient Information:
- Name: {patient['name']}
- Age: {patient['age']} years
- Gender: {patient['gender']}
- Reported Symptoms: {patient['symptoms']}
- Blood Pressure: {patient.get('bp', 'Not recorded')}
- Blood Sugar Level: {patient.get('sugar_level', 'Not recorded')}
- Body Temperature: {patient.get('temperature', 'Not recorded')}


Please provide:
1. URGENCY LEVEL: (Emergency / High / Medium / Low) - one word only
2. POSSIBLE CONDITIONS: List 2 to 3 possible medical conditions
3. RECOMMENDED TESTS: List 2 to 3 tests the doctor should order
4. IMMEDIATE ACTION: One sentence on what should happen next


Keep your response clear, concise, and in simple English.
Do not provide a final diagnosis. This is a triage suggestion for the attending nurse.
"""
    return prompt




def run_triage(patient: dict) -> dict:
    """
    DATA ANALYST FUNCTION: Sends patient data to Groq AI and returns the result.


    This is the main function called by main.py.
    Steps:
      1. Call build_prompt(patient) to create the message
      2. Send the message to Groq AI
      3. Extract the text from the response
      4. Return a clean dictionary with the result
    """


    # Step 1: Build the prompt using the patient's data
    prompt = build_prompt(patient)


    # Step 2: Call the Groq API
    # messages is a list of conversation turns
    # role='user' means this is what we (the user) are asking
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                'role': 'user',
                'content': prompt
            }
        ],
        temperature=0.3,   # 0 = very consistent. 1 = very creative.
                           # For medical use, we want consistent answers, not creative ones.
        max_tokens=500     # Maximum length of the AI response
    )


    # Step 3: Extract the AI's text from the response object
    # The Groq response has a nested structure:
    # response.choices[0].message.content is where the AI's text lives
    ai_text = response.choices[0].message.content


    # Step 4: Return a clean dictionary with the result
    return {
        'patient_id':   patient['id'],
        'patient_name': patient['name'],
        'age':          patient['age'],
        'gender':       patient['gender'],
        'symptoms':     patient['symptoms'],
        'ai_response':  ai_text,
        'model_used':   GROQ_MODEL
    }
