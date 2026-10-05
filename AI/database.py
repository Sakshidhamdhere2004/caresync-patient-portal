# FILE: database.py
# WHO WRITES THIS: Data Engineer
# WHAT THIS FILE DOES:
#   This file handles everything related to the MySQL database.
#   It has 3 functions:
#     get_connection()      - Opens a connection to MySQL
#     get_patient(id)       - Fetches one patient record by ID
#     get_all_patients()    - Fetches all patients for the dropdown
#
# The Data Analyst does NOT write SQL. They call these functions.
# ============================================================


import mysql.connector      # This package lets Python talk to MySQL
import os                   # This package reads environment variables
from dotenv import load_dotenv  # This reads values from our .env file


# Load the .env file
# After this line runs, os.getenv('DB_HOST') will return 'localhost'
load_dotenv()




def get_connection():
    """
    Opens and returns a connection to the MySQL database.
    All connection settings come from the .env file.
    If MySQL is not running or the password is wrong, this will raise an error.
    """
    connection = mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),     # MySQL server address
        user=os.getenv('DB_USER', 'root'),           # MySQL username
        password=os.getenv('DB_PASSWORD', ''),       # MySQL password
        database=os.getenv('DB_NAME', 'hospital_triage')  # Database name
    )
    return connection




def get_patient(patient_id: int):
    """
    Fetches ONE patient record from MySQL using their ID number.
    Returns a dictionary like: {'id': 1, 'name': 'Priya Sharma', 'age': 28, ...}
    Returns None if no patient with that ID exists.
    """


    # Step 1: Open a connection to MySQL
    conn = get_connection()


    # Step 2: Create a cursor
    # A cursor is like a pen - it lets us write SQL queries
    # dictionary=True means each row is returned as {column: value}
    # Without dictionary=True, rows would come back as plain tuples (0, 'Priya', 28, ...)
    cursor = conn.cursor(dictionary=True)


    # Step 3: Run the SQL query
    # We use %s as a placeholder for the patient_id value
    # This is called a parameterized query - it prevents SQL injection attacks
    # NEVER do this: f'SELECT * FROM patients WHERE id = {patient_id}'
    # That would allow hackers to inject SQL code
    cursor.execute('SELECT * FROM patients WHERE id = %s', (patient_id,))


    # Step 4: Fetch the single result row
    patient = cursor.fetchone()


    # Step 5: Always close cursor and connection when done
    # This frees up the database connection for other requests
    cursor.close()
    conn.close()


    # Return the patient dict, or None if not found
    return patient




def get_all_patients():
    """
    Fetches ALL patients from the database.
    Used by the web page dropdown to show all patient names.
    Returns a list of dictionaries: [{id, name, age, gender}, ...]
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)


    # Only fetch id, name, age, gender - we don't need symptoms here
    # ORDER BY id means patients appear in order: 1, 2, 3, ..., 10
    cursor.execute('SELECT id, name, age, gender FROM patients ORDER BY id')


    patients = cursor.fetchall()  # fetchall() returns a list of ALL rows


    cursor.close()
    conn.close()


    return patients

