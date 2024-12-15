from fastapi import FastAPI
import sqlite3
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "http://localhost:4200",
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
    cursor.execute("SELECT course_z_code, objective_text FROM objectives")
    objectives = cursor.fetchall()

    # Create a mapping of course_z_code to objectives
    objectives_by_course = {}
    for obj in objectives:
        course_z_code = obj["course_z_code"]
        if course_z_code not in objectives_by_course:
            objectives_by_course[course_z_code] = []
        objectives_by_course[course_z_code].append(obj["objective_text"])  # Only include objective_text
        
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
