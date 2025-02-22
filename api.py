from fastapi import FastAPI
import sqlite3
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from models.course import Course
from models.verification import Verification

app = FastAPI()

origins = [
    "http://localhost:4200",
    "http://localhost:6694",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Function to fetch courses with objectives and child courses
def get_courses_with_objectives():
    connection = sqlite3.connect("courses.db")
    connection.row_factory = sqlite3.Row  # Access rows as dictionaries
    cursor = connection.cursor()

    # Fetch all courses
    cursor.execute("SELECT * FROM courses ORDER BY phase_is_mandatory DESC")
    courses = cursor.fetchall()

    # Fetch objectives grouped by course_z_code
    cursor.execute("SELECT course_z_code, objective_text_nl, objective_text_en FROM objectives")
    objectives = cursor.fetchall()

    # Create a mapping of course_z_code to objectives
    objectives_by_course = {}
    for obj in objectives:
        course_z_code = obj["course_z_code"]
        if course_z_code not in objectives_by_course:
            objectives_by_course[course_z_code] = []
        objectives_by_course[course_z_code].append({
            "nl": obj["objective_text_nl"],
            "en": obj["objective_text_en"]
        })  # Opslaan als dictionary
        
    # Fetch tags grouped by course_z_code
    cursor.execute(
        """
        SELECT ct.course_z_code, t.name 
        FROM course_tag ct
        JOIN tags t ON ct.tag_id = t.id
        """
    )
    tags = cursor.fetchall()
    
    # Create a mapping of course_z_code to tags
    tags_by_course = {}
    for tag in tags:
        course_z_code = tag["course_z_code"]
        if course_z_code not in tags_by_course:
            tags_by_course[course_z_code] = []
        tags_by_course[course_z_code].append(tag["name"])  # Only include name

    # Create a mapping of z_code to course data
    courses_dict = {course["z_code"]: dict(course) for course in courses}

    # Process each course and add objectives, tags, and child courses
    for course in courses_dict.values():
        course["objectives"] = objectives_by_course.get(course["z_code"], [])  # Default to empty list
        course["tags"] = tags_by_course.get(course["z_code"], [])  # Default to empty list
        course["childs"] = []  # Initialize child courses list

    # Assign child courses to parents
    for course in courses_dict.values():
        parent_course_str = course.get("parent_course")
        if parent_course_str:
            parent_z_codes = [z.strip() for z in parent_course_str.split(",") if z.strip()]
            for parent_z_code in parent_z_codes:
                if parent_z_code in courses_dict:
                    courses_dict[parent_z_code]["childs"].append(course)

    connection.close()
    return list(courses_dict.values())  # Convert back to list


# Function to fetch tags
def get_tags():
    tag = sqlite3.connect("courses.db")
    tag.row_factory = sqlite3.Row  # Access rows as dictionaries
    cursor = tag.cursor()

    # Fetch all courses
    cursor.execute("SELECT * FROM tags ORDER BY name asc")
    tags = cursor.fetchall()

    # Convert each row to a dictionary
    tags_list = [dict(row) for row in tags]

    tag.close()
    return tags_list

# Function to fetch profiles
def get_profiles():
    profile = sqlite3.connect("courses.db")
    profile.row_factory = sqlite3.Row  # Access rows as dictionaries
    cursor = profile.cursor()

    # Fetch all courses
    cursor.execute("SELECT * FROM profiles")
    profiles = cursor.fetchall()

    # Convert each row to a formatted dictionary
    profiles_list = [
        {
            "name": row["name"],
            "img": row["img"],
            "route": row["route"],
            "title": {
                "nl": row["title_nl"],
                "en": row["title_en"]
            },
            "description": {
                "nl": row["description_nl"],
                "en": row["description_en"]
            }
        }
        for row in profiles
    ]

    profile.close()
    return profiles_list


def insert_course(course: Course):
    conn = sqlite3.connect("courses.db")
    conn.row_factory = sqlite3.Row  # Access rows as dictionaries
    cursor = conn.cursor()

    # Check if course already exists
    cursor.execute("SELECT * FROM courses WHERE z_code = ? AND status = 'APPROVED'", (course.z_code,))
    original_course = cursor.fetchone()

    
    cursor.execute("SELECT * FROM courses WHERE z_code = ? AND status = 'PENDING'", (course.z_code,))
    existingduplicate_course = cursor.fetchone()

    if existingduplicate_course:
        # If a duplicate course with status PENDING exists, UPDATE the course record
        cursor.execute("""
            UPDATE courses 
            SET summary_nl = ?, summary_en = ?, credits = ?
            WHERE z_code = ?
        """, (
            course.summary, 
            course.summaryEnglish, 
            course.credits,
            course.z_code
        ))
        course_id = existingduplicate_course["z_code"]
    else:
        # If no duplicate course with status PENDING exists, INSERT the new course
        cursor.execute("""
            INSERT INTO courses 
            (z_code, 
            course_name, 
            phase, 
            phase_is_mandatory, 
            summary_nl, 
            summary_en, semester, learning_contents_nl, learning_contents_en, 
            learning_track_id, programme, language, credits, parent_course, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            original_course["z_code"] + "_pending", 
            original_course["course_name"], 
            original_course["phase"], 
            original_course["phase_is_mandatory"], 
            course.summary, 
            course.summaryEnglish, 
            original_course["semester"], 
            original_course["learning_contents_nl"], 
            "",
            original_course["learning_track_id"], 
            original_course["programme"], 
            original_course["language"],
            original_course["credits"],
            original_course["parent_course"],
            "PENDING"
        ))
        course_id = original_course["z_code"] + "_pending"

    # Delete objectives
    cursor.execute("DELETE FROM objectives WHERE course_z_code = ?", (course_id,))

    # Insert objectives
    for obj in course.objectives:
        cursor.execute("""
            INSERT INTO objectives (course_z_code, objective_text_nl, objective_text_en)
            VALUES (?, ?, ?)
        """, (course_id, obj.nl, obj.en))

    # Delete tags
    cursor.execute("DELETE FROM course_tag WHERE course_z_code = ?", (course_id,))
    
    # Insert tags
    for tag_name in course.tags:
        # Look up tag_id from the tags table
        cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
        tag_row = cursor.fetchone()

        if tag_row:
            tag_id = tag_row["id"]

            # Insert into course_tag table
            cursor.execute("""
                INSERT INTO course_tag (course_z_code, tag_id)
                VALUES (?, ?)
            """, (course_id, tag_id))
        else:
            print(f"Tag '{tag_name}' not found in database.")

    # Commit and close
    conn.commit()
    conn.close()

@app.get("/courses")
async def get_all_courses():
    try:
        courses = get_courses_with_objectives()
        return JSONResponse(content=courses, status_code=200)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/tags")
async def get_all_tags():
    try:
        tags = get_tags()
        return JSONResponse(content=tags, status_code=200)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/profiles")
async def get_all_profiles():
    try:
        profiles = get_profiles()
        return JSONResponse(content=profiles, status_code=200)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/add_course/")
async def add_course(course: Course):
    try:
        insert_course(course)
        return JSONResponse(content="Course added successfully", status_code=200)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
    
@app.post("/verification")
async def verify(request: Verification):
    # Hier kan je de validatie en logica toevoegen
    if request.key == "9f7a3c5d1e8b6f02c4a9d7e3b5f1c8a0":
        # Migration van pending naar real course
        # Check of de z_code eindigt op "_pending"
        if not request.z_code.endswith("_pending"):
            return {"status": "error", "message": "Course not migrateable"}

        # Bepaal de echte course z_code (zonder '_pending')
        real_z_code = request.z_code.replace("_pending", "")

        connection = sqlite3.connect("courses.db")
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        # Haal de pending course op
        cursor.execute("SELECT * FROM courses WHERE z_code = ?", (request.z_code,))
        pending_course = cursor.fetchone()

        if not pending_course:
            connection.close()
            return {"status": "error", "message": "Pending course niet gevonden."}

        # Check of de echte course al bestaat
        cursor.execute("SELECT * FROM courses WHERE z_code = ?", (real_z_code,))
        real_course = cursor.fetchone()

        if not real_course:
            connection.close()
            return {"status": "error", "message": "Echte course niet gevonden."}

        # Update de echte course met gegevens van de pending course
        cursor.execute("""
            UPDATE courses 
            SET summary_nl = ?, summary_en = ?, credits = ?
            WHERE z_code = ?
        """, (pending_course["summary_nl"], pending_course["summary_en"], 
            pending_course["credits"], real_z_code))

        # Haal alle objectives van de pending course op
        cursor.execute("SELECT * FROM objectives WHERE course_z_code = ?", (request.z_code,))
        objectives = cursor.fetchall()
        
        # Verwijder eerst alle objectives van de echte course
        cursor.execute("DELETE FROM objectives WHERE course_z_code = ?", (real_z_code,))

        # Zet de objectives over naar de echte course
        for obj in objectives:
            cursor.execute("""
                INSERT INTO objectives (course_z_code, objective_text_nl, objective_text_en)
                VALUES (?, ?, ?)
            """, (real_z_code, obj["objective_text_nl"], obj["objective_text_en"]))
            
        # Verwijder eerst alle tags van de echte course
        cursor.execute("DELETE FROM course_tag WHERE course_z_code = ?", (real_z_code,))

        # Haal alle tags van de pending course op
        cursor.execute("SELECT * FROM course_tag WHERE course_z_code = ?", (request.z_code,))
        tags = cursor.fetchall()
    
        # Zet de tags over naar de echte course
        for tag in tags:
            cursor.execute("""
                INSERT INTO course_tag (course_z_code, tag_id)
                VALUES (?, ?)
            """, (real_z_code, tag["tag_id"]))


        # Pas status pending course aan, zodat we hem niet meer zien, tenzij we dat echt willen
        cursor.execute("""
            UPDATE courses 
            SET status = 'ARCHIVED'
            WHERE z_code = ?
        """, (request.z_code,))

        connection.commit()
        connection.close()

        return {"message": "Verification gelukt!"}  
    return {"status": "error", "message": "Invalid credentials"}