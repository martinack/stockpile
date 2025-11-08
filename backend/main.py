# --- main.py ---
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
import qrcode
import uuid
import os
from datetime import datetime
from typing import Optional, List
from fastapi.middleware.cors import CORSMiddleware  # <-- CORS import hinzugefügt

# --- Datenbank Setup ---
DATABASE_URL = "sqlite:///./data/storage.db"
#DATABASE_URL = "sqlite:///./data/storage.db"
os.makedirs("data", exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    name = Column(String)
    quantity = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    warehouse = relationship("Warehouse", back_populates="items")

class Warehouse(Base):
    __tablename__ = "warehouses"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    location = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    items = relationship("Item", back_populates="warehouse")

Base.metadata.create_all(bind=engine)

# Sanfte Migration: füge fehlende Spalten hinzu (nur für SQLite)
with engine.connect() as conn:
    # Stelle sicher, dass Tabelle 'warehouses' existiert
    Base.metadata.create_all(bind=engine)
    # Prüfe, ob 'warehouse_id' in 'items' existiert, sonst hinzufügen
    result = conn.exec_driver_sql("PRAGMA table_info(items);")
    columns = [row[1] for row in result.fetchall()]
    if "warehouse_id" not in columns:
        conn.exec_driver_sql("ALTER TABLE items ADD COLUMN warehouse_id INTEGER;")
    if "quantity" not in columns:
        conn.exec_driver_sql("ALTER TABLE items ADD COLUMN quantity TEXT;")

# --- FastAPI Setup ---
app = FastAPI(title="Food Storage Backend")

# CORS-Konfiguration
# Passe die Origins an deine Frontend-URL(s) an (z. B. Angular Dev-Server)
origins = [
    "http://localhost:8080",
    # "http://127.0.0.1:4200",
    # "https://deine-domain.tld",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # oder: ["*"] für alle (nicht mit Credentials kombinieren)
    allow_credentials=True,          # nur aktivieren, wenn du Cookies/Auth-Header brauchst
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],             # oder spezifische Header-Whitelist
    expose_headers=["Content-Disposition"],  # falls du bestimmte Response-Header sichtbar machen willst
)


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

# ... existing code ...
@app.post("/items/", response_model=dict)
def create_item(item: ItemCreate):
    db = SessionLocal()
    code = str(uuid.uuid4())[:8]  # kurzer eindeutiger Code
    # Optional: prüfe Warehouse, falls gesetzt
    warehouse = None
    if item.warehouse_id is not None:
        warehouse = db.query(Warehouse).filter(Warehouse.id == item.warehouse_id, Warehouse.is_active == True).first()
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found or inactive")

    db_item = Item(code=code, name=item.name, quantity=item.quantity, warehouse_id=item.warehouse_id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    # QR-Code erzeugen
    if not os.path.exists("qrcodes"):
        os.makedirs("qrcodes")
    img = qrcode.make(f"{db_item.code}")
    file_path = f"qrcodes/{db_item.code}.png"
    img.save(file_path)

    return {"id": db_item.id, "code": db_item.code, "qr_code": file_path, "quantity": db_item.quantity, "warehouse_id": db_item.warehouse_id}

# ... existing code ...
@app.get("/items/", response_model=List[dict])
def list_items(active_only: bool = True, search: Optional[str] = None):
    """
    List all items with optional search by name.
    """
    db = SessionLocal()
    query = db.query(Item)

    if active_only:
        query = query.filter(Item.is_active == True)

    if search:
        query = query.filter(Item.name.ilike(f"%{search}%"))

    items = query.order_by(Item.created_at.desc()).all()

    return [
        {
            "id": it.id,
            "name": it.name,
            "code": it.code,
            "quantity": it.quantity,
            "created_at": it.created_at,
            "is_active": it.is_active,
            "warehouse_id": it.warehouse_id,
        }
        for it in items
    ]

@app.get("/items/{code}", response_model=dict)
def get_item(code: str):
    db = SessionLocal()
    db_item = db.query(Item).filter(Item.code == code, Item.is_active == True).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    return {
        "id": db_item.id,
        "name": db_item.name,
        "code": db_item.code,
        "quantity": db_item.quantity,
        "created_at": db_item.created_at,
        "is_active": db_item.is_active,
        "warehouse_id": db_item.warehouse_id,
    }

# ... existing code ...
@app.delete("/items/{item_id}", response_model=dict)
def delete_item(item_id: int):
    """
    Delete an item by ID.
    """
    db = SessionLocal()
    db_item = db.query(Item).filter(Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Remove QR code file if exists
    qr_path = f"qrcodes/{db_item.code}.png"
    if os.path.exists(qr_path):
        os.remove(qr_path)

    db.delete(db_item)
    db.commit()
    return {"message": "Item deleted", "id": item_id}

@app.post("/items/{code}/checkout")
def checkout_item(code: str):
    db = SessionLocal()
    db_item = db.query(Item).filter(Item.code == code, Item.is_active == True).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found or already checked out")
    db_item.is_active = False
    db.commit()
    return {"message": f"Item {code} checked out"}

@app.post("/items/{code}/move", response_model=dict)
def move_item(code: str, warehouse_id: Optional[int] = None):
    """
    Verschiebt ein Item in ein anderes Warehouse oder entkoppelt es (warehouse_id=None).
    """
    db = SessionLocal()
    db_item = db.query(Item).filter(Item.code == code, Item.is_active == True).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found or inactive")

    if warehouse_id is not None:
        warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id, Warehouse.is_active == True).first()
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found or inactive")
    db_item.warehouse_id = warehouse_id
    db.commit()
    db.refresh(db_item)
    return {"id": db_item.id, "code": db_item.code, "warehouse_id": db_item.warehouse_id}

@app.get("/qrcode/{code}")
def get_qrcode(code: str):
    file_path = f"qrcodes/{code}.png"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="QR Code not found")
    return FileResponse(file_path, media_type="image/png")

@app.post("/warehouses/", response_model=dict)
def create_warehouse(warehouse: WarehouseCreate):
    db = SessionLocal()
    existing = db.query(Warehouse).filter(Warehouse.name == warehouse.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Warehouse with this name already exists")
    db_wh = Warehouse(name=warehouse.name, location=warehouse.location)
    db.add(db_wh)
    db.commit()
    db.refresh(db_wh)
    return {
        "id": db_wh.id,
        "name": db_wh.name,
        "location": db_wh.location,
        "created_at": db_wh.created_at,
        "is_active": db_wh.is_active,
    }

@app.get("/warehouses/", response_model=List[dict])
def list_warehouses(active_only: bool = True):
    db = SessionLocal()
    query = db.query(Warehouse)
    if active_only:
        query = query.filter(Warehouse.is_active == True)
    warehouses = query.order_by(Warehouse.name.asc()).all()
    return [
        {
            "id": wh.id,
            "name": wh.name,
            "location": wh.location,
            "created_at": wh.created_at,
            "is_active": wh.is_active,
        }
        for wh in warehouses
    ]

@app.get("/warehouses/{warehouse_id}", response_model=dict)
def get_warehouse(warehouse_id: int):
    db = SessionLocal()
    wh = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not wh:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return {
        "id": wh.id,
        "name": wh.name,
        "location": wh.location,
        "created_at": wh.created_at,
        "is_active": wh.is_active,
    }

@app.delete("/warehouses/{warehouse_id}", response_model=dict)
def delete_warehouse(warehouse_id: int):
    db = SessionLocal()
    wh = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not wh:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    # Items entkoppeln, um FK-Probleme beim Löschen zu vermeiden
    items = db.query(Item).filter(Item.warehouse_id == warehouse_id).all()
    for it in items:
        it.warehouse_id = None
    db.delete(wh)
    db.commit()
    return {"message": "Warehouse deleted", "id": warehouse_id}



@app.patch("/warehouses/{warehouse_id}", response_model=dict)
def update_warehouse(warehouse_id: int, payload: WarehouseUpdate):
    db = SessionLocal()
    wh = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not wh:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    if payload.name is not None:
        # Prüfe auf Namenskonflikte
        conflict = db.query(Warehouse).filter(Warehouse.name == payload.name, Warehouse.id != warehouse_id).first()
        if conflict:
            raise HTTPException(status_code=400, detail="Another warehouse with this name exists")
        wh.name = payload.name
    if payload.location is not None:
        wh.location = payload.location
    if payload.is_active is not None:
        wh.is_active = payload.is_active
    db.commit()
    db.refresh(wh)
    return {
        "id": wh.id,
        "name": wh.name,
        "location": wh.location,
        "created_at": wh.created_at,
        "is_active": wh.is_active,
    }

@app.get("/warehouses/{warehouse_id}/items", response_model=List[dict])
def list_items_in_warehouse(warehouse_id: int, active_only: bool = True):
    db = SessionLocal()
    # Validierung Warehouse
    wh = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not wh:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    query = db.query(Item).filter(Item.warehouse_id == warehouse_id)
    if active_only:
        query = query.filter(Item.is_active == True)
    items = query.order_by(Item.created_at.desc()).all()
    return [
        {
            "id": it.id,
            "name": it.name,
            "code": it.code,
            "quantity": it.quantity,
            "created_at": it.created_at,
            "is_active": it.is_active,
            "warehouse_id": it.warehouse_id,
        }
        for it in items
    ]
