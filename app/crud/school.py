from app.crud.base import CRUDBase
from app.models.address import Address
from app.models.school import School


address = CRUDBase(Address)
school = CRUDBase(School)