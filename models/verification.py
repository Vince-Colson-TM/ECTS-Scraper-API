from pydantic import BaseModel
class Verification(BaseModel):
    z_code: str
    key: str