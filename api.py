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
    cursor.execute("SELECT * FROM courses")
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

    # Combine course data with objectives
    courses_with_objectives = []
    for course in courses:
        course_dict = dict(course)  # Convert SQLite Row to dictionary
        course_dict["objectives"] = objectives_by_course.get(course["z_code"], [])  # Default to empty list
        courses_with_objectives.append(course_dict)

    connection.close()
    return courses_with_objectives


# Function to fetch connections
def get_connections():
    connection = sqlite3.connect("courses.db")
    connection.row_factory = sqlite3.Row  # Access rows as dictionaries
    cursor = connection.cursor()

    # Fetch all courses
    cursor.execute("SELECT * FROM course_connections")
    connections = cursor.fetchall()

    # Convert each row to a dictionary
    connections_list = [dict(row) for row in connections]

    connection.close()
    return connections_list


@app.get("/courses")
async def get_all_courses():
    try:
        courses = get_courses_with_objectives()
        return JSONResponse(content=courses, status_code=200)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/connections")
async def get_all_connections():
    try:
        connections = get_connections()
        return JSONResponse(content=connections, status_code=200)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
