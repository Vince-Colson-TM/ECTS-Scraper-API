import time
import requests
from bs4 import BeautifulSoup
import sqlite3
import warnings
import logging
import re

# TODO - Change naming to be more accurate across the codebase
# TODO - Remove redundant code and functions
# TODO - Get credits from overview page
# TODO - Get evaluation methods from detail course page

# Set up logging
logging.basicConfig(filename='scraper.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Suppress InsecureRequestWarning
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

# URL of the overview page where Z-codes are listed
url = "https://onderwijsaanbodkempen.thomasmore.be/2024/opleidingen/n/SC_51260641.htm"

# Headers that contain the courses to scrape from the overview page
headers = [
    'Verplichte opleidingsonderdelen',
    'Artificial Intelligence / Application Development',
    'Application Development',
    # 'Artificial Intelligence',
]

# Phrases to remove from the start of learning objectives
start_phrases = ['de student', 'je', 'you']


# Function to clean and join objectives
def clean_and_join_objectives(raw_objectives):
    cleaned_objectives = []

    for obj in raw_objectives:
        # Normalize the text by removing extra spaces
        obj = obj.strip()

        # Remove unwanted phrases at the start
        for phrase in start_phrases:
            # Use word boundaries to catch the phrase at the start
            pattern = re.compile(rf'^\b{phrase}\b\s+', re.IGNORECASE)
            obj = re.sub(pattern, '', obj)

        # Remove trailing period if it exists
        obj = obj.rstrip('.').strip()

        # Capitalize the first letter if not empty
        if obj:
            obj = obj[0].upper() + obj[1:]

        cleaned_objectives.append(obj)

    return cleaned_objectives


# Function to clean text data (e.g., course names)
def clean_text(text):
    # Remove various list markers including •, -, *, and numbered lists
    return re.sub(r'^[•\-*]|\d+\.?\)?\s*', '', text.strip())

    # Remove period at the end of the sentence (but preserve other special characters)
    text = re.sub(r'\.\s*$', '', text)

    # Normalize spaces
    cleaned_text = ' '.join(text.split())  # Remove extra spaces

    return cleaned_text


def scrape_courses(overview_url, headers_to_scrape):
    """
    Scrape course data for specified headers from the provided overview URL.

    Args:
        overview_url (str): URL of the overview page.
        headers_to_scrape (list): List of headers to scrape, e.g., ['Verplichte opleidingsonderdelen'].

    Returns:
        list: A list of dictionaries containing scraped course data.
    """
    try:
        response = requests.get(overview_url, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        logging.info(f"Fetched HTML content from {overview_url}")
        all_courses = []

        for header_text in headers_to_scrape:
            header = soup.find(lambda tag: tag.name == 'h3' and header_text == tag.get_text().strip())
            if not header:
                logging.warning(f"Could not find header: {header_text}")
                continue

            parent_li = header.find_parent('li')
            if not parent_li:
                logging.warning(f"Could not find parent <li> for header: {header_text}")
                continue

            rows = parent_li.find_all('tr')
            logging.info(f"Total rows found under header '{header_text}': {len(rows)}")

            for index, row in enumerate(rows, 1):
                if is_element_hidden(row):
                    continue

                # Extract Z-code
                z_code_element = row.find('td', class_='code')
                z_code = z_code_element.get_text().strip() if z_code_element else None

                # Extract Course Name
                course_name_td = row.find('td', class_='opleidingsonderdeel')
                course_name = course_name_td.get_text(strip=True) if course_name_td else None

                # Assuming `row` is the <tr> element containing all <td> elements
                fase_tds = row.find_all('td', class_='fase')  # Get all td elements with class 'fase'

                for phase_td in fase_tds:
                    img_tag = phase_td.find('img')
                    if img_tag and 'src' in img_tag.attrs:
                        img_src = img_tag['src']
                        print(f"img_src for fase: {img_src}")  # Debugging line
                        match = re.search(r'icon-fase(\d+)-([mo])\.png', img_src)

                        # Check if the match is found
                        if match:
                            phase = int(match.group(1))  # Extract phase number
                            phase_is_mandatory = match.group(2) == 'm'  # 'm' for mandatory, 'o' for optional
                            print(f"Found phase {phase}, mandatory: {phase_is_mandatory}")  # Debugging line
                        else:
                            # If no match, check for the case where 'o' might not be captured
                            match_no_mandatory = re.search(r'icon-fase(\d+)\.png', img_src)
                            if match_no_mandatory:
                                phase = int(match_no_mandatory.group(1))  # Extract phase number
                                phase_is_mandatory = False  # Assume false if only the phase is captured
                                print(f"Found phase {phase}, mandatory: {phase_is_mandatory}")  # Debugging line
                            else:
                                print("No match found for img_src")  # Debugging line
                    else:
                        print("No img tag or src attribute found in this fase_td")  # Debugging line

                # Extract Semester
                semester_number = None
                semester_td = row.find('td', class_='sem')
                if semester_td:
                    sem_img_tag = semester_td.find('img')
                    if sem_img_tag and 'src' in sem_img_tag.attrs:
                        semester_match = re.search(r'icon-semester-(\d+)\.png', sem_img_tag['src'])
                        if semester_match:
                            semester_number = int(semester_match.group(1))

                if z_code:
                    all_courses.append({
                        "z_code": z_code,
                        "course_name": course_name,
                        "phase": phase,
                        "phase_is_mandatory": phase_is_mandatory,
                        "semester": semester_number,
                    })

                    logging.debug(
                        f"Scraped Z-code: {z_code}, Course: {course_name}, Phase: {phase}, Semester: {semester_number}")

        logging.info(f"Total courses scraped: {len(all_courses)}")
        return all_courses

    except Exception as e:
        logging.error(f"Failed to scrape courses: {e}")
        return []


def is_element_hidden(element):
    """Check if an element is hidden based on various criteria."""
    # Check inline style
    if element.has_attr('style'):
        style = element['style'].lower()
        if 'display: none' in style or 'visibility: hidden' in style:
            return True

    # Check classes
    if element.has_attr('class'):
        classes = element.get('class', [])
        hidden_classes = ['hidden', 'invisible', 'intranet']
        if any(cls in classes for cls in hidden_classes):
            return True

    # Check for 'hidden' attribute
    if element.has_attr('hidden'):
        return True

    # Check for aria-hidden attribute
    if element.has_attr('aria-hidden') and element['aria-hidden'].lower() == 'true':
        return True

    # Check for custom data attributes that might indicate hiding
    for attr, value in element.attrs.items():
        if attr.startswith('data-') and ('hidden' in attr or 'visible' in attr):
            if value.lower() in ['false', '0', 'no', 'hidden']:
                return True

    return False


# Function to filter out unwanted entries
def is_valid_objective(text):
    # List of phrases to filter out
    filter_phrases = [
        'De student:',
        # 'De student',
        # 'Je',
        'In ',
        'General Competences',
        'Knowledge',
        'Skills',
        'Attitudes',
        'Competences',
        'Learning outcomes'
    ]

    # Check if the text is empty or too short
    if not text.strip() or len(text.strip()) < 10:
        return False

    # Normalize the text for comparison
    normalized_text = text.strip().lower()

    # Check if the text starts with any of the filter phrases
    if any(normalized_text.startswith(phrase.lower()) for phrase in filter_phrases):
        return False

    # Further checks can be added here if needed

    return True


# Function to try fetching content from the Z-code with different suffixes
def fetch_with_suffixes(z_code):
    suffixes = ["N", "E", ""]
    base_url = "https://onderwijsaanbodkempen.thomasmore.be/2024/syllabi/n/"

    for suffix in suffixes:
        try:
            url = f"{base_url}{z_code}{suffix}.htm"
            response = requests.get(url, verify=False)  # Disable SSL verification (not recommended for production)
            response.raise_for_status()  # Raise an error if the page is not found
            return BeautifulSoup(response.text, 'html.parser'), url  # Return the soup and URL if successful
        except requests.exceptions.RequestException:
            continue  # Try the next suffix if the request fails
    return None, None  # Return None if all attempts fail


def scrape_courses_data(course_data):
    for course in course_data:
        z_code = course['z_code']
        soup, final_url = fetch_with_suffixes(z_code)

        # Default values to ensure all keys exist
        course['objectives'] = []
        course['learning_contents'] = ''

        if soup:
            try:
                # Objectives extraction (same as original)
                objectives_div = soup.find(id=lambda x: x and x.startswith("tab_doelstellingen_idp"))
                objectives = set()

                if objectives_div:
                    list_items = objectives_div.find_all('li')
                    for li in list_items:
                        objective_text = li.get_text().strip().replace('\xa0', ' ')
                        if objective_text and is_valid_objective(objective_text):
                            objectives.add(objective_text)

                    paragraphs = objectives_div.find_all('p')
                    for p in paragraphs:
                        full_text = p.get_text(separator='<br>').strip()
                        split_objectives = full_text.split('<br>')
                        for obj in split_objectives:
                            normalized_obj = obj.strip().replace('\xa0', ' ')
                            cleaned_obj = clean_text(normalized_obj)

                            if cleaned_obj and is_valid_objective(cleaned_obj):
                                objectives.add(cleaned_obj)

                cleaned_objectives = clean_and_join_objectives(list(objectives))
                course['objectives'] = cleaned_objectives

                # Find all divs that match the content pattern
                contents_divs = soup.find_all('div',
                    id=lambda x: x and x.startswith('tab_inhoud_') and x.endswith('_content'))

                if contents_divs:
                    # Collect contents from all matching divs
                    all_contents = []
                    for contents_div in contents_divs:
                        # Remove print-only tags
                        for tag in contents_div.find_all(class_='print_only'):
                            tag.decompose()

                        # Preserve some attributes
                        allowed_attrs = ['id', 'class']
                        for attr in list(contents_div.attrs.keys()):
                            if attr not in allowed_attrs:
                                del contents_div.attrs[attr]

                        # Convert to string, preserving HTML structure
                        cleaned_contents = str(contents_div)
                        if cleaned_contents.strip():
                            all_contents.append(cleaned_contents)

                    # Join multiple content divs
                    course['learning_contents'] = '\n'.join(all_contents)

                print(f"Successfully scraped course: {course['course_name']} from {final_url}")

            except Exception as e:
                print(f"Failed to process data for {z_code}: {e}")
        else:
            print(f"Failed to retrieve page for Z-code {z_code}.")

    return course_data


# Function to create and set up the database
def setup_database():
    conn = sqlite3.connect('courses.db')
    cursor = conn.cursor()

    # Drop tables if they exist to start fresh
    cursor.execute('DROP TABLE IF EXISTS objectives')
    cursor.execute('DROP TABLE IF EXISTS course_tags')
    cursor.execute('DROP TABLE IF EXISTS courses')
    cursor.execute('DROP TABLE IF EXISTS tags')

    # Create tables for storing course and objectives data
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS courses (
        z_code TEXT PRIMARY KEY,
        course_name TEXT,
        phase INTEGER,
        phase_is_mandatory BOOLEAN,
        semester INTEGER,
        learning_contents TEXT,
        learning_path TEXT,
        language TEXT
        UNIQUE(z_code, course_name)
    )
    ''')
    
    # Table to store tags
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tag_name TEXT NOT NULL UNIQUE
    )
    ''')

    # Table to store many-to-many relationships between courses and tags
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS course_tags (
    course_z_code TEXT NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (course_z_code, tag_id),
    FOREIGN KEY (course_z_code) REFERENCES courses(z_code) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS objectives (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_z_code TEXT,
        objective_text TEXT,
        FOREIGN KEY (course_z_code) REFERENCES courses(z_code)
    )
    ''')    

    return conn, cursor


# Function to insert data into the database
def insert_data(conn, cursor, course_data):
    for course in course_data:
        cursor.execute('''INSERT OR REPLACE INTO courses (z_code, course_name, phase, phase_is_mandatory, semester, 
        learning_contents) VALUES (?, ?, ?, ?, ?, ?)''',
                       (course['z_code'],
                        course['course_name'],
                        course.get('phase'),
                        course.get('phase_is_mandatory'),
                        course.get('semester'),
                        course.get('learning_contents') or ''))
        print(f"Inserted data for course: {course['course_name']}")

        objectives = course.get('objectives', [])
        for objective in objectives:
            if objective:
                cursor.execute('''INSERT INTO objectives (course_z_code, objective_text)
                                  VALUES (?, ?)''',
                               (course['z_code'], objective))
                print(f"Inserted objective for {course['course_name']}: {objective}")

    conn.commit()


# Main execution function
def main():
    # Scrape Z-codes from the overview page
    courses = scrape_courses(url, headers)

    # Check if Z-codes were successfully scraped
    if courses:
        print(f"Scraped {len(courses)} courses from overview.")

        # Scrape course data
        course_data = scrape_courses_data(courses)

        # Set up the database
        conn, cursor = setup_database()

        # Insert the scraped data into the database
        insert_data(conn, cursor, course_data)

        # Close the database connection
        conn.close()

        print("Data scraping and insertion complete.")
    else:
        print("No Z-codes found. Scraping aborted.")


# Run the main function
if __name__ == "__main__":
    main()
