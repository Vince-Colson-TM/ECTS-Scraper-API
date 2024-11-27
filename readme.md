# ECTS Scraper and API

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/Vince-Colson-TM/ECTS-Scraper-API.git
   cd ECTS-Scraper-API
     ```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Optional: Run the scraper to repopulate the database with updated course information:

```bash
python scraper.py
```

4. Start the API server:

```bash
uvicorn api:app --reload --port 8000
```
Access the API at the chosen port e.g. http://127.0.0.1:8000.
Documentation at http://127.0.0.1:8000/docs.
GET /courses to retrieve all courses.

Example response:
```json
{
  "z_code": "Z26280",
  "course_name": "Data Essentials",
  "phase": 1,
  "phase_is_mandatory": 1,
  "semester": 1,
  "learning_contents": "<div><p><p>1. Datamodellering:</p><ul><li>Inleiding tot datamodellering</li><li>Begrippen primary key, foreign key, alternate key, constraints</li><li>Herkennen en benoemen van verschillende soorten relaties</li></ul><p>2. SQL:</p><ul><li>CREATE TABLE, INSERT, UPDATE, DELETE</li><li>SELECT-component</li><li>WHERE-component</li><li>Scalaire functies</li><li>Joins</li><li>Subquery’s</li><li>SET-functies</li><li>GROUP BY</li></ul><p>Doorheen het semester wordt deze leerstof toegepast in een project.</p><p>3. Document-georiënteerde databases</p><p> </p></p></div>",
  "objectives": [
    "Vraagt gegevens op uit een relationele databank op aan de hand van SQL queries",
    "Zet een set van eisen correct om in een passend relationeel datamodel",
    "Maakt, wijzigt en verwijdert tabellen en records in een relationele databank",
    "Interpreteert een datamodel op correcte wijze",
    "Maakt een relationele databank aan in een DBMS",
    "Bevraagt een document-georiënteerde databank"
  ]
},
```
