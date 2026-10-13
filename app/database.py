from sqlmodel import SQLModel, create_engine

from app.models import Candidatura  # noqa: F401  (hace falta para que se cree la tabla)

engine = create_engine("sqlite:///candidaturas.db")


def crear_tablas():
    SQLModel.metadata.create_all(engine)


if __name__ == "__main__":
    crear_tablas()
    print("Base de datos creada")
