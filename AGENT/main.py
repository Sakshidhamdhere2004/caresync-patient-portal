# ============================================================
# FILE: main.py
# ROLE: Data Analyst (DA)
# PURPOSE: FastAPI server
#
# START:
#     uvicorn main:app --reload
#
# URL:
#     http://localhost:8000
# ============================================================


from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

import re


# ============================================================
# DATABASE
# ============================================================

from database import (
    get_patient,
    get_all_patients,
    auto_discharge_patient
)


# ============================================================
# AI TRIAGE
# ============================================================

from triage_ai import run_triage


# ============================================================
# MCP TOOLS
# ============================================================

from mcp_tools import (
    tool_check_bed,
    tool_get_on_duty_nurse,
    tool_assign_bed
)


# ============================================================
# BED AI AGENT
# ============================================================

from bed_agent import run_agent


# ============================================================
# CREATE FASTAPI APP
# ============================================================

app = FastAPI(
    title="Hospital Triage and Bed Agent API",
    version="1.0.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"]
)


# ============================================================
# HOME PAGE
# ============================================================

@app.get("/")
def serve_homepage():
    """
    Sends index.html to the browser.
    """

    return FileResponse("index.html")


# ============================================================
# PATIENTS
# ============================================================

@app.get("/patients")
def list_patients():
    """
    Returns all patients.
    """

    return get_all_patients()


# ============================================================
# TRIAGE
# ============================================================

@app.post("/triage/{patient_id}")
def do_triage(patient_id: int):
    """
    Gets a patient and runs AI triage.
    """

    patient = get_patient(patient_id)

    if not patient:

        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    result = run_triage(patient)

    return {
        "success": True,
        "patient_id": patient_id,
        "result": result
    }


# ============================================================
# MCP TOOL REQUEST MODELS
# ============================================================

class BedRequest(BaseModel):

    ward: str


class NurseRequest(BaseModel):

    ward: str


class AssignRequest(BaseModel):

    patient_id: int

    bed_id: int

    nurse_name: str


# ============================================================
# MCP TOOL:
# CHECK BED
# ============================================================

@app.post("/tools/check_bed")
def api_check_bed(req: BedRequest):
    """
    Finds an empty bed in the requested ward.
    """

    result = tool_check_bed(req.ward)

    return result


# ============================================================
# MCP TOOL:
# GET ON-DUTY NURSE
# ============================================================

@app.post("/tools/get_on_duty_nurse")
def api_get_nurse(req: NurseRequest):
    """
    Finds the nurse currently on duty in the ward.
    """

    result = tool_get_on_duty_nurse(req.ward)

    return result


# ============================================================
# MCP TOOL:
# ASSIGN BED
# ============================================================

@app.post("/tools/assign_bed")
def api_assign_bed(req: AssignRequest):
    """
    Assigns patient to a bed and nurse.
    """

    result = tool_assign_bed(
        req.patient_id,
        req.bed_id,
        req.nurse_name
    )

    return result


# ============================================================
# AGENT REQUEST
# ============================================================

class AgentRequest(BaseModel):

    patient_id: int

    ward: str


# ============================================================
# HELPER:
# EXTRACT BED NUMBER FROM AGENT TEXT
# ============================================================

def extract_bed_id(text):
    """
    Extracts a bed number from the AI agent response.

    Examples supported:

        Bed #35
        Bed 35
        bed #35
        bed 35
        bed number 35
    """

    if not text:
        return None

    patterns = [

        r"Bed\s*#\s*(\d+)",

        r"Bed\s+number\s+(\d+)",

        r"Bed\s+(\d+)",

        r"bed_id\s*[:=]\s*(\d+)"

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return int(match.group(1))

    return None


# ============================================================
# HELPER:
# EXTRACT NURSE NAME
# ============================================================

def extract_nurse_name(text):
    """
    Extracts nurse name from the AI response.

    Example:

        Nurse Kavya Iyer

        nurse on duty — Kavya Iyer

        Nurse: Kavya Iyer
    """

    if not text:
        return None


    patterns = [

        r"nurse\s+on\s+duty\s*[-:—]\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)+)",

        r"nurse\s*[:\-—]\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)+)",

        r"nurse\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)+)"

    ]


    for pattern in patterns:

        match = re.search(
            pattern,
            text
        )

        if match:

            name = match.group(1).strip()

            # Remove accidental trailing punctuation
            name = name.rstrip(".,;:")

            return name


    return None


# ============================================================
# HELPER:
# DETERMINE ASSIGNMENT SUCCESS
# ============================================================

def assignment_was_successful(text):
    """
    Determines whether the AI agent successfully
    assigned a bed.
    """

    if not text:
        return False


    lower = text.lower()


    success_phrases = [

        "successfully assigned",

        "assigned to bed",

        "assigned patient",

        "patient has been assigned",

        "bed has been assigned",

        "assignment successful"

    ]


    for phrase in success_phrases:

        if phrase in lower:

            return True


    return False


# ============================================================
# BED AGENT ENDPOINT
# ============================================================

@app.post("/agent/assign_bed")
def agent_assign_bed(req: AgentRequest):
    """
    Runs the AI bed-allocation agent.

    The agent should:

        1. Check available bed
        2. Find on-duty nurse
        3. Assign patient to bed
        4. Return result

    The endpoint converts the agent response into
    structured JSON for the browser.
    """

    # --------------------------------------------------------
    # CHECK PATIENT
    # --------------------------------------------------------

    patient = get_patient(req.patient_id)

    if not patient:

        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )


    # --------------------------------------------------------
    # VALIDATE WARD
    # --------------------------------------------------------

    allowed_wards = [

        "General",

        "Emergency",

        "ICU",

        "Pediatric",

        "Maternity"

    ]


    if req.ward not in allowed_wards:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid ward '{req.ward}'. "
                f"Allowed wards: {', '.join(allowed_wards)}"
            )
        )


    # --------------------------------------------------------
    # RUN AI AGENT
    # --------------------------------------------------------

    try:

        agent_response = run_agent(
            req.patient_id,
            req.ward
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Bed agent failed: {str(e)}"
        )


    # --------------------------------------------------------
    # NORMALIZE AGENT RESPONSE
    # --------------------------------------------------------

    if isinstance(
        agent_response,
        dict
    ):

        result_text = str(
            agent_response.get(
                "result",
                agent_response
            )
        )

    else:

        result_text = str(
            agent_response
        )


    # --------------------------------------------------------
    # DETERMINE SUCCESS
    # --------------------------------------------------------

    success = assignment_was_successful(
        result_text
    )


    # --------------------------------------------------------
    # EXTRACT BED
    # --------------------------------------------------------

    bed_id = extract_bed_id(
        result_text
    )


    # --------------------------------------------------------
    # EXTRACT NURSE
    # --------------------------------------------------------

    nurse_name = extract_nurse_name(
        result_text
    )


    # --------------------------------------------------------
    # RETURN STRUCTURED RESPONSE
    # --------------------------------------------------------

    return {

        "success": success,

        "patient_id": req.patient_id,

        "patient_name": (
            patient.get("name")
            if isinstance(patient, dict)
            else None
        ),

        "ward": req.ward,

        "bed_id": bed_id,

        "nurse_name": nurse_name,

        "assigned": success,

        "result": result_text

    }


# ============================================================
# DISCHARGE REQUEST
# ============================================================

class DischargeRequest(BaseModel):

    patient_id: int


# ============================================================
# ACTUAL PATIENT DISCHARGE
# ============================================================

@app.post("/patient/discharge")
def discharge_patient(
    req: DischargeRequest
):
    """
    Actually discharges a patient.

    This is intentionally separate from bed assignment.

    Steps:

        1. Find active bed
        2. Create discharge record
        3. Release bed
        4. Make bed available
    """

    patient = get_patient(
        req.patient_id
    )

    if not patient:

        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )


    result = auto_discharge_patient(
        req.patient_id
    )


    if not result.get("success"):

        raise HTTPException(

            status_code=400,

            detail=result.get(
                "message",
                "Unable to discharge patient"
            )

        )


    return result


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():

    return {

        "status": "ok",

        "service":
            "Hospital Triage and Bed Agent API"

    }


# ============================================================
# RUN DIRECTLY
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )