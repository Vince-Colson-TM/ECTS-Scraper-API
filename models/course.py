from pydantic import BaseModel

class Course(BaseModel):
    z_code: str
    summary: str
    summaryEnglish: str