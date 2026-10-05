# ============================================================
# FILE: main.py
# ROLE: Data Analyst (DA)
# PURPOSE: FastAPI server. Runs on http://localhost:8000
#
# New in Day 11:
#   POST /tools/check_bed         -- MCP tool: find empty bed
#   POST /tools/get_on_duty_nurse -- MCP tool: find on-duty nurse
#   POST /tools/assign_bed        -- MCP tool: assign bed to patient
#
# HOW TO START: uvicorn main:app --reload
# ============================================================
 
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from database import get_patient, get_all_patients
from triage_ai import run_triage
from mcp_tools import tool_check_bed, tool_get_on_duty_nurse, tool_assign_bed
 
# Create FastAPI app
app = FastAPI(title="Hospital Triage and Bed Agent API")
 
# Allow browser to call this API
# Without this, the browser will block all requests (CORS policy)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # Allow all websites (safe for development)
    allow_methods=["*"],    # Allow GET, POST, etc.
    allow_headers=["*"],
)
 
 
# ============================================================
# FROM DAY 10 -- Original routes (no change)
# ============================================================
 
@app.get("/")
def serve_homepage():
    """Sends the index.html file to the browser."""
    return FileResponse("index.html")
 
 
@app.get("/patients")
def list_patients():
    """Returns all patients from the database as a JSON list."""
    return get_all_patients()
 
 
@app.post("/triage/{patient_id}")
def do_triage(patient_id: int):
    """
    Gets one patient from database and runs AI triage.
    Returns the AI triage result as a string.
    """
    patient = get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    result = run_triage(patient)
    return {"result": result}
 
 
# ============================================================
# NEW FOR DAY 11 -- MCP Tool routes
# These are the endpoints the AI Agent calls.
# ============================================================
 
# Pydantic models define the JSON format for POST request bodies
 
class BedRequest(BaseModel):
    ward: str           # Example: "General"
 
 
class NurseRequest(BaseModel):
    ward: str           # Example: "ICU"
 
 
class AssignRequest(BaseModel):
    patient_id: int     # Example: 5
    bed_id: int         # Example: 4
    nurse_name: str     # Example: "Sunita Patil"
 
 
@app.post("/tools/check_bed")
def api_check_bed(req: BedRequest):
    """
    MCP Tool endpoint: Check for empty bed in a ward.
    The AI agent calls this as its first step.
    """
    return tool_check_bed(req.ward)
 
 
@app.post("/tools/get_on_duty_nurse")
def api_get_nurse(req: NurseRequest):
    """
    MCP Tool endpoint: Get on-duty nurse in a ward.
    The AI agent calls this as its second step.
    """
    return tool_get_on_duty_nurse(req.ward)
 
 
@app.post("/tools/assign_bed")
def api_assign_bed(req: AssignRequest):
    """
    MCP Tool endpoint: Assign a patient to a bed.
    The AI agent calls this as its final step.
    This writes to the database.
    """
    return tool_assign_bed(req.patient_id, req.bed_id, req.nurse_name)

# ============================================================
# Add this at the bottom of main.py
# This route is called by the browser HTML button.
# It runs the bed agent and returns the result.
# ============================================================
 
# Import the agent function
from bed_agent import run_agent
 
 
class AgentRequest(BaseModel):
    patient_id: int
    ward: str
 
 
@app.post("/agent/assign_bed")
def agent_assign_bed(req: AgentRequest):
    """
    Runs the AI agent to assign a bed.
    The browser HTML button calls this endpoint.
    The agent talks to Groq AI and calls MCP tools to do the assignment.
    """
    result = run_agent(req.patient_id, req.ward)
    return {"result": result}




