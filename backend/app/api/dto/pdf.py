from pydantic import BaseModel


class SkillModel(BaseModel):
    name:str


class AchievementModel(BaseModel):
    text:str
    impact:str
    metrics:str
 
class ProjectModel(BaseModel):
    name:str
    company:str
    achievements:list[AchievementModel]
    skills:list[SkillModel]

