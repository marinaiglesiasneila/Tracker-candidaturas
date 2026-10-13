from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

import app.main as main
from app.models import Candidatura


@pytest.fixture
def engine(monkeypatch):
    """Base de datos SQLite en memoria, nueva para cada test."""
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)
    monkeypatch.setattr(main, "engine", test_engine)
    return test_engine


@pytest.fixture
def client(engine):
    return TestClient(main.app)


def crear(client, empresa="Acme", puesto="Data analyst"):
    return client.post("/candidaturas", json={"empresa": empresa, "puesto": puesto})


# ---------- API ----------


def test_crear_candidatura_usa_valores_por_defecto(client):
    r = crear(client)
    assert r.status_code == 200
    datos = r.json()
    assert datos["id"] == 1
    assert datos["estado"] == "enviada"
    assert datos["fecha"] == date.today().isoformat()


def test_crear_sin_empresa_da_422(client):
    r = client.post("/candidaturas", json={"puesto": "Data analyst"})
    assert r.status_code == 422


def test_crear_con_estado_invalido_da_400(client):
    r = client.post(
        "/candidaturas",
        json={"empresa": "Acme", "puesto": "X", "estado": "inventado"},
    )
    assert r.status_code == 400


def test_listar_y_filtrar_por_estado(client):
    crear(client, "A")
    crear(client, "B")
    client.patch("/candidaturas/2", params={"estado": "entrevista"})

    assert len(client.get("/candidaturas").json()) == 2
    entrevistas = client.get("/candidaturas", params={"estado": "entrevista"}).json()
    assert [c["empresa"] for c in entrevistas] == ["B"]


def test_cambiar_estado(client):
    crear(client)
    r = client.patch("/candidaturas/1", params={"estado": "oferta"})
    assert r.status_code == 200
    assert r.json()["estado"] == "oferta"


def test_cambiar_estado_inexistente_da_404(client):
    r = client.patch("/candidaturas/999", params={"estado": "oferta"})
    assert r.status_code == 404


def test_cambiar_a_estado_invalido_da_400(client):
    crear(client)
    r = client.patch("/candidaturas/1", params={"estado": "inventado"})
    assert r.status_code == 400


def test_borrar_y_borrar_otra_vez(client):
    crear(client)
    assert client.delete("/candidaturas/1").json() == {"ok": True}
    assert client.delete("/candidaturas/1").status_code == 404


# ---------- Web ----------


def test_pagina_principal_vacia(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Aún no hay ninguna" in r.text


def test_formulario_crea_candidatura_y_redirige(client, engine):
    r = client.post(
        "/nueva",
        data={"empresa": "  Acme  ", "puesto": "Dev", "enlace": ""},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/"
    with Session(engine) as session:
        fila = session.exec(select(Candidatura)).one()
    assert fila.empresa == "Acme"  # sin espacios sobrantes
    assert fila.enlace is None  # enlace vacío se guarda como None


def test_cambiar_estado_desde_web(client, engine):
    crear(client)
    r = client.post("/estado/1", data={"estado": "entrevista"}, follow_redirects=False)
    assert r.status_code == 303
    with Session(engine) as session:
        assert session.get(Candidatura, 1).estado == "entrevista"


def test_borrar_desde_web(client, engine):
    crear(client)
    client.post("/borrar/1", follow_redirects=False)
    with Session(engine) as session:
        assert session.get(Candidatura, 1) is None


def test_filtro_en_la_pagina_principal(client):
    crear(client, "Empresa-Uno")
    crear(client, "Empresa-Dos")
    client.patch("/candidaturas/2", params={"estado": "oferta"})
    html = client.get("/", params={"estado": "oferta"}).text
    assert "Empresa-Dos" in html
    assert "Empresa-Uno" not in html


# ---------- Lógica de seguimiento ----------


@pytest.mark.parametrize(
    "estado, dias, esperado",
    [
        ("enviada", 7, True),
        ("enviada", 20, True),
        ("enviada", 6, False),
        ("entrevista", 30, False),
        ("rechazada", 30, False),
    ],
)
def test_necesita_seguimiento(estado, dias, esperado):
    c = Candidatura(
        empresa="X",
        puesto="Y",
        estado=estado,
        fecha=date.today() - timedelta(days=dias),
    )
    assert main.necesita_seguimiento(c) is esperado


def test_la_pagina_muestra_aviso_de_seguimiento(client):
    client.post(
        "/candidaturas",
        json={
            "empresa": "Antigua",
            "puesto": "X",
            "fecha": (date.today() - timedelta(days=10)).isoformat(),
        },
    )
    html = client.get("/").text
    assert "Sin respuesta, 10 días" in html
