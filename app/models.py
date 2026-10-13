from datetime import date
from typing import Optional

from sqlmodel import Field, SQLModel


class Candidatura(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    empresa: str
    puesto: str
    estado: str = "enviada"
    fecha: date = Field(default_factory=date.today)
    enlace: Optional[str] = None
    notas: Optional[str] = None


class CandidaturaCrear(SQLModel):
    """Datos que acepta la API para crear una candidatura.

    Los modelos con table=True no validan lo que reciben; este sí,
    y además impide que el cliente elija el id.
    """

    empresa: str
    puesto: str
    estado: str = "enviada"
    fecha: date = Field(default_factory=date.today)
    enlace: Optional[str] = None
    notas: Optional[str] = None
