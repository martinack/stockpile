from __future__ import annotations

import json
import os
import uuid
from collections.abc import Generator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Literal, Optional

import httpx
import qrcode
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, create_engine, text
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker

Base = declarative_base()


class Unit(Base):
    __tablename__ = "units"
    id = Column(Integer, primary_key=True)
    name = Column(String(80), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    items = relationship("Item", back_populates="unit")


class Warehouse(Base):
    __tablename__ = "warehouses"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), unique=True, nullable=False, index=True)
    location = Column(String(255))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    items = relationship("Item", back_populates="warehouse")


class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    code = Column(String(32), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    quantity_value = Column(Numeric(12, 3), nullable=False)
    storage_date = Column(Date, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"))
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)
    warehouse = relationship("Warehouse", back_populates="items")
    unit = relationship("Unit", back_populates="items")


@dataclass(frozen=True)
class Settings:
    database_url: str
    qrcodes_dir: Path
    solr_url: str | None
    create_schema: bool = False

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(os.getenv("DATABASE_URL", "postgresql+psycopg://stockpile:stockpile@postgres:5432/stockpile"), Path(os.getenv("STOCKPILE_QRCODES_DIR", "qrcodes")), os.getenv("SOLR_URL", "http://solr:8983/solr/stockpile"))


class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    quantity_value: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    unit_id: int
    warehouse_id: Optional[int] = None
    storage_date: Optional[date] = None


class WarehouseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    location: Optional[str] = None


class WarehouseUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    is_active: Optional[bool] = None


class UnitCreate(BaseModel): name: str = Field(min_length=1, max_length=80)
class UnitUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


class SolrIndex:
    def __init__(self, url: str): self.url = url.rstrip("/")
    def request(self, method: str, path: str, **kwargs) -> dict:
        result = httpx.request(method, f"{self.url}{path}", timeout=10, **kwargs); result.raise_for_status(); return result.json()
    def ensure_schema(self) -> None:
        fields = [("item_id_i", "pint", True), ("name_text", "text_general", False), ("name_sort_s", "string", True), ("code_s", "string", True), ("warehouse_id_i", "pint", True), ("warehouse_name_s", "string", True), ("unit_id_i", "pint", True), ("unit_name_s", "string", True), ("quantity_value_d", "pdouble", True), ("storage_date_dt", "pdate", True), ("active_b", "boolean", True), ("created_at_dt", "pdate", True)]
        for name, kind, doc_values in fields:
            response = httpx.post(f"{self.url}/schema", json={"add-field": {"name": name, "type": kind, "stored": True, "indexed": True, "docValues": doc_values}}, timeout=10)
            if response.status_code not in (200, 400): response.raise_for_status()
    def reindex(self, db: Session) -> None:
        """Replace the derived index with PostgreSQL's current inventory state."""
        documents = [document(item) for item in db.query(Item).join(Unit).outerjoin(Warehouse).all()]
        # Solr's JSON update format does not allow a delete command and bare
        # documents in the same array (the delete would be parsed as a
        # document/atomic update).  Clear first, then add the authoritative
        # PostgreSQL projection and commit it.
        self.request("POST", "/update", json={"delete": {"query": "*:*"}})
        self.request("POST", "/update?commit=true", json=documents if documents else {"commit": {}})
    def search(self, **filters) -> dict:
        q = filters.pop("q") or "*:*"; page = filters.pop("page"); size = filters.pop("page_size")
        fq = ["active_b:true"]
        for key, field in (("warehouse_id", "warehouse_id_i"), ("unit_id", "unit_id_i")):
            if filters[key] is not None: fq.append(f"{field}:{filters[key]}")
        if filters["storage_date_from"] or filters["storage_date_to"]: fq.append(f"storage_date_dt:[{filters['storage_date_from'] or '*'}T00:00:00Z TO {filters['storage_date_to'] or '*'}T23:59:59Z]")
        facets = {"warehouses": {"type": "terms", "field": "warehouse_id_i", "limit": -1, "facet": {"name": "min(warehouse_name_s)"}}, "units": {"type": "terms", "field": "unit_id_i", "limit": -1, "facet": {"name": "min(unit_name_s)"}}, "storage_date": {"type": "range", "field": "storage_date_dt", "start": "NOW/DAY-30DAYS", "end": "NOW/DAY+24MONTHS", "gap": "+1MONTH"}, "storage_date_min": "min(storage_date_dt)", "storage_date_max": "max(storage_date_dt)"}
        sort_field = {"name": "name_sort_s", "storage_date": "storage_date_dt"}[filters["sort_by"]]
        sort = f"{sort_field} {filters['sort_direction']},created_at_dt desc"
        data = self.request("GET", "/select", params={"wt": "json", "defType": "edismax", "q": q, "qf": "name_text^3 code_s", "fq": fq, "start": (page-1)*size, "rows": size, "sort": sort, "json.facet": json.dumps(facets)})
        return {"items": [search_response(doc) for doc in data["response"]["docs"]], "total": data["response"]["numFound"], "facets": data.get("facets", {})}


def document(item: Item) -> dict:
    result = {"id": f"item-{item.id}", "item_id_i": item.id, "name_text": item.name, "name_sort_s": item.name.casefold(), "code_s": item.code, "warehouse_id_i": item.warehouse_id, "warehouse_name_s": item.warehouse.name if item.warehouse else "", "unit_id_i": item.unit_id, "unit_name_s": item.unit.name, "quantity_value_d": float(item.quantity_value), "active_b": item.is_active, "created_at_dt": item.created_at.isoformat()}
    # Solr does not consistently accept JSON null for a single-valued date field.
    if item.storage_date:
        result["storage_date_dt"] = f"{item.storage_date.isoformat()}T00:00:00Z"
    return result

def search_response(doc: dict) -> dict:
    return {"id": doc["item_id_i"], "name": doc["name_text"], "code": doc["code_s"], "quantity_value": doc["quantity_value_d"], "unit_id": doc["unit_id_i"], "unit_name": doc["unit_name_s"], "warehouse_id": doc.get("warehouse_id_i"), "warehouse_name": doc.get("warehouse_name_s") or None, "storage_date": doc.get("storage_date_dt"), "created_at": doc.get("created_at_dt")}

def unit_response(unit: Unit) -> dict: return {"id": unit.id, "name": unit.name, "is_active": unit.is_active, "created_at": unit.created_at}
def warehouse_response(warehouse: Warehouse) -> dict: return {"id": warehouse.id, "name": warehouse.name, "location": warehouse.location, "created_at": warehouse.created_at, "is_active": warehouse.is_active}
def item_response(item: Item) -> dict: return {"id": item.id, "name": item.name, "code": item.code, "quantity_value": item.quantity_value, "unit_id": item.unit_id, "unit_name": item.unit.name, "storage_date": item.storage_date, "created_at": item.created_at, "is_active": item.is_active, "warehouse_id": item.warehouse_id, "warehouse_name": item.warehouse.name if item.warehouse else None}

def get_db(request: Request) -> Generator[Session, None, None]:
    db = request.app.state.session_factory()
    try: yield db
    finally: db.close()
DbSession = Annotated[Session, Depends(get_db)]
router = APIRouter()
def sync(request: Request, db: Session) -> None:
    if request.app.state.solr: request.app.state.solr.reindex(db)

@router.get("/health")
def health(request: Request) -> dict:
    """Readiness health check used by Docker and Caddy dependencies."""
    try:
        with request.app.state.session_factory() as db:
            db.execute(text("SELECT 1"))
        if request.app.state.solr:
            request.app.state.solr.request("GET", "/admin/ping")
    except Exception as exc:
        raise HTTPException(503, "Dependencies are not ready") from exc
    return {"status": "ok"}

@router.get("/units/")
def list_units(db: DbSession, active_only: bool = True) -> list[dict]:
    query = db.query(Unit); query = query.filter(Unit.is_active.is_(True)) if active_only else query
    return [unit_response(x) for x in query.order_by(Unit.id).all()]
@router.get("/units/{unit_id}")
def get_unit(unit_id: int, db: DbSession) -> dict:
    unit = db.get(Unit, unit_id)
    if not unit: raise HTTPException(404, "Unit not found")
    return unit_response(unit)
@router.post("/units/")
def create_unit(payload: UnitCreate, db: DbSession, request: Request) -> dict:
    if db.query(Unit).filter(Unit.name == payload.name).first(): raise HTTPException(400, "Unit already exists")
    unit = Unit(name=payload.name); db.add(unit); db.commit(); db.refresh(unit); sync(request, db); return unit_response(unit)
@router.patch("/units/{unit_id}")
def update_unit(unit_id: int, payload: UnitUpdate, db: DbSession, request: Request) -> dict:
    unit = db.get(Unit, unit_id)
    if not unit: raise HTTPException(404, "Unit not found")
    if payload.name is not None: unit.name = payload.name
    if payload.is_active is not None: unit.is_active = payload.is_active
    db.commit(); db.refresh(unit); sync(request, db); return unit_response(unit)
@router.delete("/units/{unit_id}")
def delete_unit(unit_id: int, db: DbSession, request: Request) -> dict:
    unit = db.get(Unit, unit_id)
    if not unit: raise HTTPException(404, "Unit not found")
    unit.is_active = False; db.commit(); sync(request, db); return {"message": "Unit deactivated", "id": unit_id}

@router.post("/items/")
def create_item(payload: ItemCreate, db: DbSession, request: Request) -> dict:
    unit = db.query(Unit).filter(Unit.id == payload.unit_id, Unit.is_active.is_(True)).first()
    if not unit: raise HTTPException(404, "Unit not found or inactive")
    if payload.warehouse_id is not None and not db.query(Warehouse).filter(Warehouse.id == payload.warehouse_id, Warehouse.is_active.is_(True)).first(): raise HTTPException(404, "Warehouse not found or inactive")
    item = Item(code=str(uuid.uuid4())[:8], name=payload.name, quantity_value=payload.quantity_value, unit_id=payload.unit_id, warehouse_id=payload.warehouse_id, storage_date=payload.storage_date)
    db.add(item); db.commit(); db.refresh(item); qrcode.make(item.code).save(request.app.state.settings.qrcodes_dir / f"{item.code}.png"); sync(request, db)
    return {**item_response(item), "qr_code": f"qrcodes/{item.code}.png"}
@router.get("/items/search/")
def search_items(request: Request, q: str | None = None, warehouse_id: int | None = None, unit_id: int | None = None, storage_date_from: date | None = None, storage_date_to: date | None = None, sort_by: Literal["name", "storage_date"] = "storage_date", sort_direction: Literal["asc", "desc"] = "asc", page: int = 1, page_size: int = 50) -> dict:
    if not request.app.state.solr: raise HTTPException(503, "Search is not configured")
    if storage_date_from and storage_date_to and storage_date_from > storage_date_to: raise HTTPException(422, "Storage date range is invalid")
    return request.app.state.solr.search(q=q, warehouse_id=warehouse_id, unit_id=unit_id, storage_date_from=storage_date_from, storage_date_to=storage_date_to, sort_by=sort_by, sort_direction=sort_direction, page=max(page, 1), page_size=min(max(page_size, 1), 100))
@router.get("/items/{code}")
def get_item(code: str, db: DbSession) -> dict:
    item = db.query(Item).filter(Item.code == code, Item.is_active.is_(True)).first()
    if not item: raise HTTPException(404, "Item not found")
    return item_response(item)
@router.delete("/items/{item_id}")
def delete_item(item_id: int, db: DbSession, request: Request) -> dict:
    item = db.get(Item, item_id)
    if not item: raise HTTPException(404, "Item not found")
    path = request.app.state.settings.qrcodes_dir / f"{item.code}.png"
    if path.exists(): path.unlink()
    db.delete(item); db.commit(); sync(request, db); return {"message": "Item deleted", "id": item_id}
@router.post("/items/{code}/checkout")
def checkout_item(code: str, db: DbSession, request: Request) -> dict:
    item = db.query(Item).filter(Item.code == code, Item.is_active.is_(True)).first()
    if not item: raise HTTPException(404, "Item not found or already checked out")
    item.is_active = False; db.commit(); sync(request, db); return {"message": f"Item {code} checked out"}
@router.post("/items/{code}/move")
def move_item(code: str, db: DbSession, request: Request, warehouse_id: Optional[int] = None) -> dict:
    item = db.query(Item).filter(Item.code == code, Item.is_active.is_(True)).first()
    if not item: raise HTTPException(404, "Item not found or inactive")
    if warehouse_id is not None and not db.query(Warehouse).filter(Warehouse.id == warehouse_id, Warehouse.is_active.is_(True)).first(): raise HTTPException(404, "Warehouse not found or inactive")
    item.warehouse_id = warehouse_id; db.commit(); db.refresh(item); sync(request, db); return {"id": item.id, "code": item.code, "warehouse_id": item.warehouse_id}
@router.get("/qrcode/{code}")
def get_qrcode(code: str, request: Request) -> FileResponse:
    path = request.app.state.settings.qrcodes_dir / f"{code}.png"
    if not path.exists(): raise HTTPException(404, "QR Code not found")
    return FileResponse(path, media_type="image/png")

@router.get("/warehouses/{warehouse_id}")
def get_warehouse(warehouse_id: int, db: DbSession) -> dict:
    row = db.get(Warehouse, warehouse_id)
    if not row: raise HTTPException(404, "Warehouse not found")
    return warehouse_response(row)
@router.post("/warehouses/")
def create_warehouse(payload: WarehouseCreate, db: DbSession, request: Request) -> dict:
    if db.query(Warehouse).filter(Warehouse.name == payload.name).first(): raise HTTPException(400, "Warehouse already exists")
    row = Warehouse(name=payload.name, location=payload.location); db.add(row); db.commit(); db.refresh(row); sync(request, db); return warehouse_response(row)
@router.get("/warehouses/")
def list_warehouses(db: DbSession, active_only: bool = True) -> list[dict]:
    query = db.query(Warehouse); query = query.filter(Warehouse.is_active.is_(True)) if active_only else query
    return [warehouse_response(x) for x in query.order_by(Warehouse.name).all()]
@router.patch("/warehouses/{warehouse_id}")
def update_warehouse(warehouse_id: int, payload: WarehouseUpdate, db: DbSession, request: Request) -> dict:
    row = db.get(Warehouse, warehouse_id)
    if not row: raise HTTPException(404, "Warehouse not found")
    if payload.name is not None: row.name = payload.name
    if payload.location is not None: row.location = payload.location
    if payload.is_active is not None: row.is_active = payload.is_active
    db.commit(); db.refresh(row); sync(request, db); return warehouse_response(row)
@router.delete("/warehouses/{warehouse_id}")
def delete_warehouse(warehouse_id: int, db: DbSession, request: Request) -> dict:
    row = db.get(Warehouse, warehouse_id)
    if not row: raise HTTPException(404, "Warehouse not found")
    for item in db.query(Item).filter(Item.warehouse_id == warehouse_id): item.warehouse_id = None
    db.delete(row); db.commit(); sync(request, db); return {"message": "Warehouse deleted", "id": warehouse_id}
@router.post("/admin/reindex")
def reindex(request: Request, db: DbSession) -> dict:
    if not request.app.state.solr: raise HTTPException(503, "Search is not configured")
    sync(request, db); return {"status": "indexed"}

def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_environment(); settings.qrcodes_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(settings.database_url, **({"connect_args": {"check_same_thread": False}} if settings.database_url.startswith("sqlite") else {}))
    if settings.create_schema: Base.metadata.create_all(engine)
    factory = sessionmaker(autoflush=False, bind=engine)
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if app.state.solr:
            app.state.solr.ensure_schema()
            with factory() as db: app.state.solr.reindex(db)
        yield
    app = FastAPI(title="Stockpile Backend", lifespan=lifespan); app.state.settings = settings; app.state.session_factory = factory; app.state.solr = SolrIndex(settings.solr_url) if settings.solr_url else None; app.include_router(router)
    return app

app = create_app()
