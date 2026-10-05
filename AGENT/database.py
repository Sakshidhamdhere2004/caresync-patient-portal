# ============================================================
# FILE: database.py
# ROLE: Database Engineer (DE)
# PURPOSE: All database read/write functions in one place.
# ============================================================
 
import mysql.connector
from dotenv import load_dotenv
import os
 
# Load secret values from .env file
load_dotenv()
 
 
def get_connection():
    """
    Opens a connection to MySQL.
    Reads DB_HOST, DB_USER, DB_PASSWORD, DB_NAME from .env file.
    """
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
    )
 
 
# ============================================================
# FROM DAY 10 -- Patient functions (no change)
# ============================================================
 
def get_patient(patient_id):
    """
    Gets one patient by their ID number.
    Returns a dictionary with all their details.
    Returns None if patient not found.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)   # dictionary=True means rows come back as dicts
    cursor.execute(
        "SELECT * FROM patients WHERE id = %s",
        (patient_id,)    # This is a tuple. The comma is important!
    )
    patient = cursor.fetchone()   # Gets the first matching row
    conn.close()
    return patient
 
 
def get_all_patients():
    """
    Gets list of all patients.
    Returns: id, name, age, gender ordered by id.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, name, age, gender FROM patients ORDER BY id"
    )
    patients = cursor.fetchall()   # Gets ALL matching rows
    conn.close()
    return patients
 
 
# ============================================================
# NEW FOR DAY 11 -- Bed and staff functions
# ============================================================
 
def find_empty_bed(ward):
    """
    Finds the first empty bed in a given ward.
    ward: string like "General", "ICU", "Emergency", "Pediatric", "Maternity"
    Returns: a dict with bed_id, bed_number, bed_type
    Returns None if no empty bed found.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT bed_id, bed_number, bed_type
        FROM beds
        WHERE ward = %s AND is_occupied = 0
        LIMIT 1
        """,
        (ward,)
    )
    bed = cursor.fetchone()
    conn.close()
    return bed    # None if no empty bed in this ward
 
 
def get_on_duty_nurse(ward):
    """
    Finds the nurse currently on duty in a ward.
    ward: string like "General", "ICU", etc.
    Returns: dict with nurse_name, shift_start, shift_end
    Returns None if no nurse currently on duty.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT nurse_name, shift_start, shift_end
        FROM staff_shifts
        WHERE ward = %s AND is_on_duty = 1
        LIMIT 1
        """,
        (ward,)
    )
    nurse = cursor.fetchone()
    conn.close()
    return nurse   # None if no one on duty
 
 
def assign_bed_to_patient(patient_id, bed_id, nurse_name):
    """
    Assigns a patient to a bed in the database.
    1. Marks the bed as occupied.
    2. Sets patient_id on the bed.
    3. Adds a record in bed_assignments table.
 
    patient_id: int
    bed_id: int
    nurse_name: string
    Returns: True if success, False if error
    """
    conn = get_connection()
    cursor = conn.cursor()
 
    try:
        # Step 1: Mark bed as occupied and link patient to bed
        cursor.execute(
            """
            UPDATE beds
            SET is_occupied = 1, patient_id = %s
            WHERE bed_id = %s
            """,
            (patient_id, bed_id)
        )
 
        # Step 2: Write a record in bed_assignments (history log)
        cursor.execute(
            """
            INSERT INTO bed_assignments
            (patient_id, bed_id, nurse_assigned, assigned_at, assigned_by)
            VALUES (%s, %s, %s, NOW(), 'ai_agent')
            """,
            (patient_id, bed_id, nurse_name)
        )
 
        conn.commit()    # Save both changes to database
        conn.close()
        return True
 
    except Exception as e:
        # If anything went wrong, undo all changes
        conn.rollback()
        conn.close()
        print(f"Database error: {e}")
        return False

    # ============================================================
# AUTOMATIC DISCHARGE + AUTOMATIC BED RELEASE
# ============================================================

def auto_discharge_patient(patient_id):
    """
    Automatically discharges a patient and releases their bed.

    Steps:
    1. Check whether patient exists.
    2. Find the patient's occupied bed.
    3. Save discharge record.
    4. Release the bed automatically.
    5. Return discharge information.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        # ----------------------------------------------------
        # Step 1: Check patient
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT *
            FROM patients
            WHERE id = %s
            """,
            (patient_id,)
        )

        patient = cursor.fetchone()

        if not patient:
            return {
                "success": False,
                "message": "Patient does not exist."
            }


        # ----------------------------------------------------
        # Step 2: Find patient's occupied bed
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                bed_id,
                ward,
                bed_number,
                bed_type
            FROM beds
            WHERE patient_id = %s
              AND is_occupied = 1
            LIMIT 1
            """,
            (patient_id,)
        )

        bed = cursor.fetchone()

        if not bed:
            return {
                "success": False,
                "message": "Patient does not have an occupied bed."
            }


        # ----------------------------------------------------
        # Step 3: Create discharge summary
        # ----------------------------------------------------

        discharge_summary = (
            f"Patient {patient['name']} "
            f"(ID: {patient['id']}) has been discharged. "
            f"Bed {bed['bed_number']} in {bed['ward']} "
            f"has been released automatically."
        )


        # ----------------------------------------------------
        # Step 4: Save discharge record
        # ----------------------------------------------------

        cursor.execute(
            """
            INSERT INTO patient_discharge
            (
                patient_id,
                bed_id,
                discharge_status,
                discharge_summary
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                patient_id,
                bed["bed_id"],
                "discharged",
                discharge_summary
            )
        )


        # ----------------------------------------------------
        # Step 5: Automatically release the bed
        # ----------------------------------------------------

        cursor.execute(
            """
            UPDATE beds
            SET
                is_occupied = 0,
                patient_id = NULL
            WHERE bed_id = %s
            """,
            (bed["bed_id"],)
        )


        # ----------------------------------------------------
        # Step 6: Save all changes
        # ----------------------------------------------------

        conn.commit()


        # ----------------------------------------------------
        # Step 7: Return result
        # ----------------------------------------------------

        return {
            "success": True,
            "message": "Patient discharged and bed released automatically.",
            "patient": patient,
            "bed": bed,
            "discharge_status": "discharged",
            "bed_status": "available",
            "discharge_summary": discharge_summary
        }


    except Exception as e:

        conn.rollback()

        print(f"Automatic discharge error: {e}")

        return {
            "success": False,
            "message": str(e)
        }


    finally:

        cursor.close()
        conn.close()