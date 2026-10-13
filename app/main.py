from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, col, select

from app.database import crear_tablas, engine
from app.models import Candidatura, CandidaturaCrear

BASE_DIR = Path(__file__).parent
ESTADOS = ["enviada", "entrevista", "oferta", "rechazada"]
DIAS_SIN_NOVEDADES = 7


@asynccontextmanager
async def lifespan(app: FastAPI):
    crear_tablas()  # la base de datos se crea sola al arrancar
    yield


app = FastAPI(title="Tracker de candidaturas", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


# ---------- Funciones auxiliares ----------


def obtener_o_404(session: Session, candidatura_id: int) -> Candidatura:
    candidatura = session.get(Candidatura, candidatura_id)
    if candidatura is None:
        raise HTTPException(status_code=404, detail="Candidatura no encontrada")
    return candidatura


def validar_estado(estado: str) -> None:
    if estado not in ESTADOS:
        raise HTTPException(
            status_code=400,
            detail=f"Estado no válido. Usa uno de: {', '.join(ESTADOS)}",
        )


def necesita_seguimiento(candidatura: Candidatura) -> bool:
    """True si sigue 'enviada' y han pasado 7 días o más desde la fecha de envío."""
    limite = date.today() - timedelta(days=DIAS_SIN_NOVEDADES)
    return candidatura.estado == "enviada" and candidatura.fecha <= limite


# ---------- API (JSON) ----------


@app.get("/candidaturas")
def listar_candidaturas(estado: Optional[str] = None):
    with Session(engine) as session:
        consulta = select(Candidatura)
        if estado:
            consulta = consulta.where(Candidatura.estado == estado)
        return session.exec(consulta).all()


@app.post("/candidaturas")
def crear_candidatura(datos: CandidaturaCrear):
    validar_estado(datos.estado)
    candidatura = Candidatura.model_validate(datos)
    with Session(engine) as session:
        session.add(candidatura)
        session.commit()
        session.refresh(candidatura)
        return candidatura


@app.patch("/candidaturas/{candidatura_id}")
def cambiar_estado(candidatura_id: int, estado: str):
    validar_estado(estado)
    with Session(engine) as session:
        candidatura = obtener_o_404(session, candidatura_id)
        candidatura.estado = estado
        session.add(candidatura)
        session.commit()
        session.refresh(candidatura)
        return candidatura


@app.delete("/candidaturas/{candidatura_id}")
def borrar_candidatura(candidatura_id: int):
    with Session(engine) as session:
        candidatura = obtener_o_404(session, candidatura_id)
        session.delete(candidatura)
        session.commit()
        return {"ok": True}


# ---------- Web (HTML) ----------


@app.get("/", response_class=HTMLResponse)
def inicio(request: Request, estado: Optional[str] = None):
    with Session(engine) as session:
        todas = session.exec(
            select(Candidatura).order_by(
                col(Candidatura.fecha).desc(), col(Candidatura.id).desc()
            )
        ).all()

    visibles = [c for c in todas if c.estado == estado] if estado in ESTADOS else todas
    contexto = {
        "candidaturas": visibles,
        "total": len(todas),
        "conteo": {e: sum(1 for c in todas if c.estado == e) for e in ESTADOS},
        "pendientes": sum(1 for c in todas if necesita_seguimiento(c)),
        "estados": ESTADOS,
        "filtro": estado if estado in ESTADOS else None,
        "necesita_seguimiento": necesita_seguimiento,
        "hoy": date.today(),
    }
    return templates.TemplateResponse(request, "index.html", contexto)


@app.post("/nueva")
def nueva_desde_formulario(
    empresa: str = Form(...),
    puesto: str = Form(...),
    enlace: str = Form(""),
):
    with Session(engine) as session:
        session.add(
            Candidatura(
                empresa=empresa.strip(),
                puesto=puesto.strip(),
                enlace=enlace.strip() or None,
            )
        )
        session.commit()
    return RedirectResponse("/", status_code=303)


@app.post("/estado/{candidatura_id}")
def cambiar_estado_desde_web(candidatura_id: int, estado: str = Form(...)):
    validar_estado(estado)
    with Session(engine) as session:
        candidatura = obtener_o_404(session, candidatura_id)
        candidatura.estado = estado
        session.add(candidatura)
        session.commit()
    return RedirectResponse("/", status_code=303)


@app.post("/borrar/{candidatura_id}")
def borrar_desde_web(candidatura_id: int):
    with Session(engine) as session:
        candidatura = session.get(Candidatura, candidatura_id)
        if candidatura:
            session.delete(candidatura)
            session.commit()
    return RedirectResponse("/", status_code=303)
