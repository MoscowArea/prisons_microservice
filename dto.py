import enum
from typing import Optional, TypeVar, Generic

from pydantic import BaseModel, Field as PydanticField, ConfigDict


class FieldType(enum.Enum):
    integer = "int"
    floating = "float"
    string = "str"
    coordinates = "coordinates"
    foreign_key = "foreign_key"


class Field(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    type: FieldType = PydanticField(default=FieldType.string)
    required: bool = True
    primary_key: bool = True
    unique: bool = True
    description: Optional[str] = None
    validation_code: Optional[str] = None


class Form(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    fields: list[Field]
    description: Optional[str]

    def __hash__(self):
        return hash(self.name)


TData = TypeVar("TData")


class ResponseModel(BaseModel, Generic[TData]):
    status_code: int
    # TODO: типизировать
    data: TData


class ErrorModel(BaseModel):
    detail: str


class PrisonResponse(BaseModel):
    model_config: ConfigDict = ConfigDict(from_attributes=True)

    id: str
    name_ru: str
    name_ua: str
    subject: str
    object_type: str
    lat: float
    lon: float
    address: str
    management: str
    employees_count: int
    prisoners_count: int
    staff: str
    contacts: str
    coordinates: Optional[str] = None


class Request(BaseModel, Generic[TData]):
    data: TData


class RequestModel(BaseModel):
    name_ru: str
    name_ua: str
    subject: str
    object_type: str
    lat: float
    lon: float
    address: str
    management: str
    employees_count: int
    prisoners_count: int
    staff: str
    contacts: str


class Filters(Request):
    pass
