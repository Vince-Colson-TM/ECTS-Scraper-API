from pydantic import BaseModel
from typing import List, Optional

class Objective(BaseModel):
    nl: str
    en: Optional[str]
    
class Course(BaseModel):
    z_code: str
    summary: str
    summaryEnglish: str
    objectives: List[Objective]  # List of Objective instances
    tags: List[str]
    credits: int