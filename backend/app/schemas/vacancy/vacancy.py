from pydantic import BaseModel


class Vacancy(BaseModel):
    name: str
    link: str
    vacancy_id: str
