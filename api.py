from fastapi import FastAPI
import sqlite3
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from models.course import Course

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


# Function to fetch courses with objectives
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

    # Combine course data with objectives
    courses_with_objectives_tags = []
    for course in courses:
        course_dict = dict(course)  # Convert SQLite Row to dictionary
        course_dict["objectives"] = objectives_by_course.get(course["z_code"], [])  # Default to empty list
        course_dict["tags"] = tags_by_course.get(course["z_code"], [])  # Default to empty list
        courses_with_objectives_tags.append(course_dict)

    connection.close()
    return courses_with_objectives_tags


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
            SET summary_nl = ?, summary_en = ?
            WHERE z_code = ?
        """, (
            course.summary, 
            course.summaryEnglish, 
            course.z_code
        ))
        course_id = course.z_code + "_pending"
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
            learning_track_id, programme, language, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            "PENDING"
        ))
        course_id = cursor.lastrowid


    # # Insert objectives
    # for obj in course.objectives:
    #     cursor.execute("""
    #         INSERT INTO course_objectives (course_id, lang, objective)
    #         VALUES (?, 'nl', ?)
    #     """, (course_id, obj.nl))

    #     cursor.execute("""
    #         INSERT INTO course_objectives (course_id, lang, objective)
    #         VALUES (?, 'en', ?)
    #     """, (course_id, obj.en))

    # # Insert tags
    # for tag in course.tags:
    #     cursor.execute("""
    #         INSERT INTO course_tags (course_id, tag)
    #         VALUES (?, ?)
    #     """, (course_id, tag))

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