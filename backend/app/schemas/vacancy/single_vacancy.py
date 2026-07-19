from pydantic import BaseModel


class SingleVacancy(BaseModel):
    job_title:str
    job_text:str