# Tracker de candidaturas

Aplicación web para llevar el control de las candidaturas de empleo: empresa, puesto, estado y fecha de envío, con filtros y aviso de seguimiento para las que llevan 7 días o más sin respuesta.

Hecha con **FastAPI**, **SQLModel** (SQLite) y plantillas **Jinja2**. Incluye una API REST con documentación automática y tests con **pytest**.

## Funcionalidades

- Añadir candidaturas (empresa, puesto y enlace opcional a la oferta)
- Cambiar el estado desde la tabla: enviada, entrevista, oferta, rechazada
- Filtrar por estado, con contador por cada uno
- Aviso en las candidaturas «enviada» sin novedades desde hace 7 días o más
- Borrar con confirmación
- API REST con CRUD completo y documentación interactiva en `/docs`

## Cómo ejecutarlo (Windows)

```powershell
git clone <url-del-repositorio>
cd tracker-candidaturas
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Abre <http://127.0.0.1:8000>. La base de datos (`candidaturas.db`) se crea sola al arrancar.

En Mac o Linux, la activación es `source .venv/bin/activate`.

## Tests

```powershell
pip install -r requirements-dev.txt
pytest
```

Los tests usan una base de datos SQLite en memoria, así que no tocan tus datos reales.

## API

| Método | Ruta | Qué hace |
|--------|------|----------|
| GET | `/candidaturas` | Lista candidaturas (filtro opcional `?estado=`) |
| POST | `/candidaturas` | Crea una candidatura (JSON) |
| PATCH | `/candidaturas/{id}?estado=` | Cambia el estado |
| DELETE | `/candidaturas/{id}` | Borra una candidatura |

## Estructura

```
app/
├── main.py        # rutas de la API y de la web
├── models.py      # tabla Candidatura y modelo de entrada
├── database.py    # conexión a SQLite
├── templates/     # HTML (Jinja2)
└── static/        # CSS
tests/
└── test_api.py
```

## Decisiones técnicas

- **Modelo de entrada separado** (`CandidaturaCrear`): los modelos SQLModel con `table=True` no validan los datos que reciben, así que la API usa un modelo aparte que sí valida y no deja elegir el `id`.
- **Validación del estado** en un solo sitio (`validar_estado`) para API y web.
- **Tests con base de datos en memoria**, para no depender de ficheros.
- **Casi sin JavaScript**: solo dos líneas (enviar el desplegable al cambiar y confirmar el borrado).
