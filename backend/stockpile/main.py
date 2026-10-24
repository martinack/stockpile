from __future__ import annotations

import os
import uuid
from collections.abc import Generator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Optional

import qrcode
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker


Base = declarative_base()


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    name = Column(String)
    quantity = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    is_active = Column(Boolean, default=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    warehouse = relationship("Warehouse", back_populates="items")


class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    location = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    is_active = Column(Boolean, default=True)
    items = relationship("Item", back_populates="warehouse")


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    qrcodes_dir: Path

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            data_dir=Path(os.getenv("STOCKPILE_DATA_DIR", "data")),
            qrcodes_dir=Path(os.getenv("STOCKPILE_QRCODES_DIR", "qrcodes")),
        )

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.data_dir / 'storage.db'}"


class ItemCreate(BaseModel):
    name: str
    quantity: Optional[str] = None
    warehouse_id: Optional[int] = None


class WarehouseCreate(BaseModel):
    name: str
    location: Optional[str] = None


class WarehouseUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    is_active: Optional[bool] = None


def item_response(item: Item) -> dict:
    return {
        "id": item.id,
        "name": item.name,
        "code": item.code,
        "quantity": item.quantity,
        "created_at": item.created_at,
        "is_active": item.is_active,
        "warehouse_id": item.warehouse_id,
    }


def warehouse_response(warehouse: Warehouse) -> dict:
    return {
        "id": warehouse.id,
        "name": warehouse.name,
        "location": warehouse.location,
        "created_at": warehouse.created_at,
        "is_active": warehouse.is_active,
    }


def get_db(request: Request) -> Generator[Session, None, None]:
    db = request.app.state.session_factory()
    try:
        yield db
    finally:
        db.close()


DbSession = Annotated[Session, Depends(get_db)]
router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/items/", response_model=dict)
def create_item(item: ItemCreate, db: DbSession, request: Request) -> dict:
    if item.warehouse_id is not None:
        warehouse = (
            db.query(Warehouse)
            .filter(Warehouse.id == item.warehouse_id, Warehouse.is_active.is_(True))
            .first()
        )
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found or inactive")

    db_item = Item(
        code=str(uuid.uuid4())[:8],
        name=item.name,
        quantity=item.quantity,
        warehouse_id=item.warehouse_id,
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    qr_path = request.app.state.settings.qrcodes_dir / f"{db_item.code}.png"
    qrcode.make(db_item.code).save(qr_path)
    return {
        "id": db_item.id,
        "code": db_item.code,
        "qr_code": f"qrcodes/{db_item.code}.png",
        "quantity": db_item.quantity,
        "warehouse_id": db_item.warehouse_id,
    }


@router.get("/items/", response_model=list[dict])
def list_items(db: DbSession, active_only: bool = True, search: Optional[str] = None) -> list[dict]:
    query = db.query(Item)
    if active_only:
        query = query.filter(Item.is_active.is_(True))
    if search:
        query = query.filter(Item.name.ilike(f"%{search}%"))
    return [item_response(item) for item in query.order_by(Item.created_at.desc()).all()]


@router.get("/items/{code}", response_model=dict)
def get_item(code: str, db: DbSession) -> dict:
    item = db.query(Item).filter(Item.code == code, Item.is_active.is_(True)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item_response(item)


@router.delete("/items/{item_id}", response_model=dict)
def delete_item(item_id: int, db: DbSession, request: Request) -> dict:
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    qr_path = request.app.state.settings.qrcodes_dir / f"{item.code}.png"
    if qr_path.exists():
        qr_path.unlink()
    db.delete(item)
    db.commit()
    return {"message": "Item deleted", "id": item_id}


@router.post("/items/{code}/checkout", response_model=dict)
def checkout_item(code: str, db: DbSession) -> dict:
    item = db.query(Item).filter(Item.code == code, Item.is_active.is_(True)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found or already checked out")
    item.is_active = False
    db.commit()
    return {"message": f"Item {code} checked out"}


@router.post("/items/{code}/move", response_model=dict)
def move_item(code: str, db: DbSession, warehouse_id: Optional[int] = None) -> dict:
    item = db.query(Item).filter(Item.code == code, Item.is_active.is_(True)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found or inactive")
    if warehouse_id is not None:
        warehouse = (
            db.query(Warehouse)
            .filter(Warehouse.id == warehouse_id, Warehouse.is_active.is_(True))
            .first()
        )
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found or inactive")
    item.warehouse_id = warehouse_id
    db.commit()
    db.refresh(item)
    return {"id": item.id, "code": item.code, "warehouse_id": item.warehouse_id}


@router.get("/qrcode/{code}")
def get_qrcode(code: str, request: Request) -> FileResponse:
    qr_path = request.app.state.settings.qrcodes_dir / f"{code}.png"
    if not qr_path.exists():
        raise HTTPException(status_code=404, detail="QR Code not found")
    return FileResponse(qr_path, media_type="image/png")


@router.post("/warehouses/", response_model=dict)
def create_warehouse(warehouse: WarehouseCreate, db: DbSession) -> dict:
    if db.query(Warehouse).filter(Warehouse.name == warehouse.name).first():
        raise HTTPException(status_code=400, detail="Warehouse with this name already exists")
    record = Warehouse(name=warehouse.name, location=warehouse.location)
    db.add(record)
    db.commit()
    db.refresh(record)
    return warehouse_response(record)


@router.get("/warehouses/", response_model=list[dict])
def list_warehouses(db: DbSession, active_only: bool = True) -> list[dict]:
    query = db.query(Warehouse)
    if active_only:
        query = query.filter(Warehouse.is_active.is_(True))
    return [warehouse_response(warehouse) for warehouse in query.order_by(Warehouse.name.asc()).all()]


@router.get("/warehouses/{warehouse_id}", response_model=dict)
def get_warehouse(warehouse_id: int, db: DbSession) -> dict:
    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return warehouse_response(warehouse)


@router.delete("/warehouses/{warehouse_id}", response_model=dict)
def delete_warehouse(warehouse_id: int, db: DbSession) -> dict:
    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    for item in db.query(Item).filter(Item.warehouse_id == warehouse_id).all():
        item.warehouse_id = None
    db.delete(warehouse)
    db.commit()
    return {"message": "Warehouse deleted", "id": warehouse_id}


@router.patch("/warehouses/{warehouse_id}", response_model=dict)
def update_warehouse(warehouse_id: int, payload: WarehouseUpdate, db: DbSession) -> dict:
    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    if payload.name is not None:
        conflict = db.query(Warehouse).filter(
            Warehouse.name == payload.name, Warehouse.id != warehouse_id
        ).first()
        if conflict:
            raise HTTPException(status_code=400, detail="Another warehouse with this name exists")
        warehouse.name = payload.name
    if payload.location is not None:
        warehouse.location = payload.location
    if payload.is_active is not None:
        warehouse.is_active = payload.is_active
    db.commit()
    db.refresh(warehouse)
    return warehouse_response(warehouse)


@router.get("/warehouses/{warehouse_id}/items", response_model=list[dict])
def list_items_in_warehouse(warehouse_id: int, db: DbSession, active_only: bool = True) -> list[dict]:
    if not db.query(Warehouse).filter(Warehouse.id == warehouse_id).first():
        raise HTTPException(status_code=404, detail="Warehouse not found")
    query = db.query(Item).filter(Item.warehouse_id == warehouse_id)
    if active_only:
        query = query.filter(Item.is_active.is_(True))
    return [item_response(item) for item in query.order_by(Item.created_at.desc()).all()]


def migrate_sqlite(engine) -> None:
    """Keep databases created by prior releases usable without a migration tool."""
    with engine.begin() as connection:
        columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(items);").fetchall()}
        if "warehouse_id" not in columns:
            connection.exec_driver_sql("ALTER TABLE items ADD COLUMN warehouse_id INTEGER;")
        if "quantity" not in columns:
            connection.exec_driver_sql("ALTER TABLE items ADD COLUMN quantity TEXT;")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_environment()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.qrcodes_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    migrate_sqlite(engine)

    app = FastAPI(title="Food Storage Backend")
    app.state.settings = settings
    app.state.session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    app.include_router(router)
    return app


app = create_app()
