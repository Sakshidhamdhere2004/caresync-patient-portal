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
# ============================================================
# DISCHARGE FUNCTIONS
# ============================================================

def discharge_patient_db(patient_id):
    """
    Verifies the patient is currently in a bed, writes a discharge record,
    and frees the bed. All in ONE transaction: either everything happens
    or nothing does.
    Returns a dict. status is "discharged" or "not_admitted" or "error".
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Is this patient currently occupying a bed? (FOR UPDATE locks the row)
        cursor.execute(
            """
            SELECT bed_id, ward, bed_number
            FROM beds
            WHERE patient_id = %s AND is_occupied = 1
            FOR UPDATE
            """,
            (patient_id,),
        )
        bed = cursor.fetchone()
        if bed is None:
            conn.rollback()
            conn.close()
            return {"status": "not_admitted"}

        # Who was the nurse, and when was the patient admitted to this bed?
        cursor.execute(
            """
            SELECT nurse_assigned, assigned_at
            FROM bed_assignments
            WHERE patient_id = %s AND bed_id = %s
            ORDER BY assigned_at DESC, assignment_id DESC
            LIMIT 1
            """,
            (patient_id, bed["bed_id"]),
        )
        assignment = cursor.fetchone() or {}

        # Write the discharge record
        cursor.execute(
            """
            INSERT INTO discharges
            (patient_id, bed_id, ward, bed_number, nurse_assigned,
             admitted_at, discharged_at, discharged_by)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), 'ai_agent')
            """,
            (patient_id, bed["bed_id"], bed["ward"], bed["bed_number"],
             assignment.get("nurse_assigned"), assignment.get("assigned_at")),
        )

        # Free the bed
        cursor.execute(
            "UPDATE beds SET is_occupied = 0, patient_id = NULL WHERE bed_id = %s",
            (bed["bed_id"],),
        )

        conn.commit()
        conn.close()
        return {"status": "discharged", **bed}

    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"Database error: {e}")
        return {"status": "error", "message": str(e)}


def release_bed_db(patient_id):
    """
    Frees the bed held by this patient.
    Safe to call twice: if discharge already freed the bed, it reports the
    bed from the latest discharge record instead of failing.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT bed_id, ward, bed_number FROM beds "
            "WHERE patient_id = %s AND is_occupied = 1 FOR UPDATE",
            (patient_id,),
        )
        bed = cursor.fetchone()

        if bed:
            cursor.execute(
                "UPDATE beds SET is_occupied = 0, patient_id = NULL WHERE bed_id = %s",
                (bed["bed_id"],),
            )
            conn.commit()
            conn.close()
            return {"status": "released", **bed}

        # Nothing occupied: check whether discharge already freed it
        cursor.execute(
            "SELECT bed_id, ward, bed_number FROM discharges "
            "WHERE patient_id = %s ORDER BY discharge_id DESC LIMIT 1",
            (patient_id,),
        )
        done = cursor.fetchone()
        conn.close()
        if done:
            return {"status": "already_released", **done}
        return {"status": "no_bed_found"}

    except Exception as e:
        conn.rollback()
        conn.close()
        return {"status": "error", "message": str(e)}


def get_discharge_summary_data(patient_id):
    """
    Joins the latest discharge record with patient details.
    Returns None if the patient has never been discharged.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT d.*, p.name, p.chief_complaint
        FROM discharges d
        JOIN patients p ON p.id = d.patient_id
        WHERE d.patient_id = %s
        ORDER BY d.discharge_id DESC
        LIMIT 1
        """,
        (patient_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return row