# FILE: main.py
# WHO WRITES THIS: Both (Data Engineer and Data Analyst together)
# WHAT THIS FILE DOES:
#   This is the FastAPI backend server. It is the glue that connects:
#     - database.py  (Data Engineer's work)
#     - triage_ai.py (Data Analyst's work)
#     - index.html   (the web page)
#
#   It creates 3 API routes (URLs):
#     GET  /              - Serves the web page (index.html)
#     GET  /patients      - Returns all patients for the dropdown
#     POST /triage/{id}   - Runs AI triage for one patient
#
# HOW TO RUN:
#   In terminal: uvicorn main:app --reload
#   Then open: http://localhost:8000
# ============================================================


from fastapi import FastAPI, HTTPException    # FastAPI is the web framework
from fastapi.middleware.cors import CORSMiddleware  # Allows web page to call our API
from fastapi.staticfiles import StaticFiles   # Serves index.html as a static file
from fastapi.responses import FileResponse    # Sends a file as the HTTP response


# Import functions from the Data Engineer's file
from database import get_patient, get_all_patients


# Import function from the Data Analyst's file
from triage_ai import run_triage


# Create the FastAPI application
# This 'app' object is what uvicorn runs when we start the server
app = FastAPI(
    title='Hospital Triage Assistant',
    description='AI-powered patient triage using Groq API and MySQL',
    version='1.0.0'
)


# ============================================================
# CORS MIDDLEWARE
# CORS = Cross-Origin Resource Sharing
# Without this, the browser blocks the web page from calling our API.
# Example: index.html is at http://localhost:8000
#          The API is also at http://localhost:8000
#          But if the HTML page was opened directly (file://), it would be blocked.
# allow_origins=['*'] means: accept requests from any address.
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],    # Allow all origins (fine for local development)
    allow_methods=['*'],    # Allow GET, POST, etc.
    allow_headers=['*'],    # Allow all headers
)


# Serve static files from the current directory
# This lets the browser load index.html
app.mount('/static', StaticFiles(directory='.'), name='static')




# ============================================================
# ROUTE 1: Root - Serves the web page
# URL: GET http://localhost:8000/
# ============================================================
@app.get('/')
def root():
    # When someone opens http://localhost:8000, send them index.html
    return FileResponse('index.html')




# ============================================================
# ROUTE 2: Get All Patients - For the web page dropdown
# URL: GET http://localhost:8000/patients
# Returns: {'patients': [{id, name, age, gender}, ...]}
# ============================================================
@app.get('/patients')
def list_patients():
    try:
        # Call the Data Engineer's function to fetch all patients
        patients = get_all_patients()
        return {'patients': patients}
    except Exception as e:
        # If MySQL is not running or credentials are wrong, return error 500
        raise HTTPException(status_code=500, detail=f'Database error: {str(e)}')




# ============================================================
# ROUTE 3: Run AI Triage - The main feature
# URL: POST http://localhost:8000/triage/{patient_id}
# Example: POST http://localhost:8000/triage/3 runs triage for Patient 3
#
# This is where the two roles meet:
#   Line 1 calls the Data Engineer's code (fetch patient from DB)
#   Line 2 calls the Data Analyst's code (send to Groq AI)
# ============================================================
@app.post('/triage/{patient_id}')
def triage_patient(patient_id: int):


    # Step 1: Fetch patient from MySQL - Data Engineer's function
    patient = get_patient(patient_id)


    # If no patient found with that ID, return error 404 (Not Found)
    if not patient:
        raise HTTPException(
            status_code=404,
            detail=f'Patient with ID {patient_id} not found.'
        )


    # Step 2: Run AI triage - Data Analyst's function
    try:
        result = run_triage(patient)
        return result
    except Exception as e:
        # If Groq API fails (wrong key, no internet, etc.), return error 500
        raise HTTPException(
            status_code=500,
            detail=f'AI triage failed: {str(e)}'
        )
