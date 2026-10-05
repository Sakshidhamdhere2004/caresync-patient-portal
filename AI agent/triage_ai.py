# ============================================================
# FILE: triage_ai.py
# ROLE: Data Analyst (DA)
# PURPOSE: Sends patient data to Groq AI and gets triage result.
# ============================================================

from groq import Groq
from dotenv import load_dotenv
import os

# Load API key from .env file
load_dotenv()

# Groq model
GROQ_MODEL = "openai/gpt-oss-20b"


def build_prompt(patient):
    """
    Takes patient dictionary and builds the AI triage prompt.

    chief_complaint is handled safely because it may come
    from the patient's symptom textbox rather than the database.
    """

    # Safely get patient information
    name = patient.get("name", "Unknown")
    age = patient.get("age", "Unknown")
    gender = patient.get("gender", "Unknown")

    # IMPORTANT:
    # The patient's symptom/complaint can come from different
    # field names depending on the frontend/backend.
    chief_complaint = (
        patient.get("chief_complaint")
        or patient.get("symptoms")
        or patient.get("complaint")
        or patient.get("description")
        or "No symptoms provided"
    )

    pain_level = patient.get("pain_level", "Not provided")
    temperature = patient.get("temperature", "Not provided")
    systolic_bp = patient.get("systolic_bp", "Not provided")
    diastolic_bp = patient.get("diastolic_bp", "Not provided")
    heart_rate = patient.get("heart_rate", "Not provided")

    return f"""
You are a hospital triage assistant.

Classify this patient's medical urgency based ONLY on the
information provided.

Patient Name: {name}
Age: {age}
Gender: {gender}

Patient's Chief Complaint / Symptoms:
{chief_complaint}

Pain Level: {pain_level} out of 10

Temperature: {temperature} Celsius

Blood Pressure: {systolic_bp}/{diastolic_bp}

Heart Rate: {heart_rate} bpm

Give the result in this format:

1. Triage Category:
   Immediate / Urgent / Semi-Urgent / Non-Urgent

2. Reason:
   Give one short sentence explaining the classification.

3. Recommended Action:
   Give a short, practical next step.

4. Recommended Doctor/Specialty:
   Suggest the most relevant medical specialty based on
   the patient's symptoms.

Important:
- Do not invent medical measurements.
- If information is missing, say that it is not provided.
- This is a preliminary triage recommendation, not a diagnosis.
- For severe or emergency symptoms, recommend immediate
  emergency medical attention.
"""


def run_triage(patient):
    """
    Sends patient data to Groq AI.
    Returns the AI response as a string.
    """

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing. Please check your .env file."
        )

    client = Groq(api_key=api_key)

    prompt = build_prompt(patient)

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.3,
        max_tokens=500,
    )

    return response.choices[0].message.content