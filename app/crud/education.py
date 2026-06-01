from app.crud.base import CRUDBase
from app.models.education_cycle import EducationCycle
from app.models.level import Level
from app.models.specialty import Specialty
from app.models.subject import Subject


education_cycle = CRUDBase(EducationCycle)
level = CRUDBase(Level)
specialty = CRUDBase(Specialty)
subject = CRUDBase(Subject)