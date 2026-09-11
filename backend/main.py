import asyncio
import os
import random
import re
import uuid
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.calle_service import calle_service
from backend.storage import (
    CallRecord,
    Offer,
    Project,
    Quote,
    QuoteItem,
    Requirement,
    Room,
    store,
)

app = FastAPI(
    title="ContractorPilot — AI Procurement & Quoting Assistant with CALL-E",
    version="1.0.0",
    description="Devpost Hackathon CALL-E: Autonomous Voice Sourcing & Professional Quoting",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")


# ------------------ Pydantic Schemas for Requests ------------------

class CreateProjectRequest(BaseModel):
    name: str
    client_name: str
    client_phone: str = ""
    client_email: str = ""
    location: str = "Alger"
    surface_sqm: float = 100.0
    project_type: str = "Rénovation d'intérieur"


class AddRoomRequest(BaseModel):
    name: str
    length: float
    width: float
    height: float = 2.70
    renovation_types: List[str] = []
    notes: str = ""


class AddRequirementRequest(BaseModel):
    room_id: Optional[str] = None
    room_name: str = ""
    category: str
    item_name: str
    quantity: float
    unit: str
    item_type: str = "material"
    estimated_unit_price: float = 0.0
    notes: str = ""


class TriggerCallRequest(BaseModel):
    project_id: str
    target_type: str  # supplier | tradesperson
    target_id: str
    requirement_id: str
    is_live: bool = False  # False for demo simulation, True for real CALL-E call


class SelectOfferRequest(BaseModel):
    project_id: str
    offer_id: str
    is_selected: bool = True


class GenerateQuoteRequest(BaseModel):
    project_id: str
    margin_percent: float = 20.0
    expenses_amount: float = 0.0
    tax_percent: float = 0.0
    currency: str = "DA"


class VoiceExtractRequest(BaseModel):
    voice_text: str
    replace_existing: bool = True


class UpdateRequirementRequest(BaseModel):
    category: Optional[str] = None
    item_name: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    item_type: Optional[str] = None
    estimated_unit_price: Optional[float] = None
    notes: Optional[str] = None


class BatchProcurementRequest(BaseModel):
    project_id: str
    is_live: bool = False


class SettingsRequest(BaseModel):
    calle_api_key: str


# ------------------ REST Endpoints ------------------

@app.get("/api/health")
async def health_check() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "app": "ContractorPilot",
        "calle_ready": calle_service.is_live_ready(),
        "calle_has_key": bool(calle_service.api_key),
    }


@app.get("/api/settings")
async def get_settings() -> Dict[str, Any]:
    masked_key = ""
    if calle_service.api_key:
        masked_key = f"{calle_service.api_key[:4]}...{calle_service.api_key[-4:]}" if len(calle_service.api_key) > 8 else "***"
    return {
        "calle_api_key_masked": masked_key,
        "is_live_ready": calle_service.is_live_ready(),
    }


@app.post("/api/settings")
async def update_settings(req: SettingsRequest) -> Dict[str, Any]:
    calle_service.update_api_key(req.calle_api_key.strip())
    return {
        "success": True,
        "is_live_ready": calle_service.is_live_ready(),
    }


@app.get("/api/suppliers")
async def list_suppliers() -> List[Dict[str, Any]]:
    return [s.model_dump() for s in store.suppliers]


@app.get("/api/tradespeople")
async def list_tradespeople() -> List[Dict[str, Any]]:
    return [t.model_dump() for t in store.tradespeople]


@app.get("/api/projects")
async def list_projects() -> List[Dict[str, Any]]:
    return [p.model_dump() for p in store.projects.values()]


@app.get("/api/projects/{project_id}")
async def get_project(project_id: str) -> Dict[str, Any]:
    proj = store.projects.get(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Projet introuvable")
    return proj.model_dump()


@app.post("/api/projects")
async def create_project(req: CreateProjectRequest) -> Dict[str, Any]:
    new_proj = Project(
        name=req.name,
        client_name=req.client_name,
        client_phone=req.client_phone,
        client_email=req.client_email,
        location=req.location,
        surface_sqm=req.surface_sqm,
        project_type=req.project_type,
        status="SITE_VISIT",
    )
    store.projects[new_proj.id] = new_proj
    store.save()
    return new_proj.model_dump()


@app.post("/api/projects/{project_id}/rooms")
async def add_room(project_id: str, req: AddRoomRequest) -> Dict[str, Any]:
    proj = store.projects.get(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Projet introuvable")

    room = Room(
        name=req.name,
        length=req.length,
        width=req.width,
        height=req.height,
        surface=round(req.length * req.width, 2),
        renovation_types=req.renovation_types,
        notes=req.notes,
    )
    proj.rooms.append(room)
    store.save()
    return room.model_dump()


@app.post("/api/projects/{project_id}/requirements")
async def add_requirement(project_id: str, req: AddRequirementRequest) -> Dict[str, Any]:
    proj = store.projects.get(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Projet introuvable")

    req_obj = Requirement(
        room_id=req.room_id,
        room_name=req.room_name,
        category=req.category,
        item_name=req.item_name,
        quantity=req.quantity,
        unit=req.unit,
        item_type=req.item_type,
        estimated_unit_price=req.estimated_unit_price,
        notes=req.notes,
    )
    proj.requirements.append(req_obj)
    store.save()
    return req_obj.model_dump()


@app.put("/api/projects/{project_id}/requirements/{requirement_id}")
async def update_requirement(project_id: str, requirement_id: str, req: UpdateRequirementRequest) -> Dict[str, Any]:
    proj = store.projects.get(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Projet introuvable")

    target = next((r for r in proj.requirements if r.id == requirement_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Besoin introuvable")

    if req.category is not None:
        target.category = req.category
    if req.item_name is not None:
        target.item_name = req.item_name
    if req.quantity is not None:
        target.quantity = req.quantity
    if req.unit is not None:
        target.unit = req.unit
    if req.item_type is not None:
        target.item_type = req.item_type
    if req.estimated_unit_price is not None:
        target.estimated_unit_price = req.estimated_unit_price
    if req.notes is not None:
        target.notes = req.notes

    store.save()
    return target.model_dump()


@app.delete("/api/projects/{project_id}/requirements/{requirement_id}")
async def delete_requirement(project_id: str, requirement_id: str) -> Dict[str, Any]:
    proj = store.projects.get(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Projet introuvable")

    initial_len = len(proj.requirements)
    proj.requirements = [r for r in proj.requirements if r.id != requirement_id]
    if len(proj.requirements) == initial_len:
        raise HTTPException(status_code=404, detail="Besoin introuvable")

    store.save()
    return {"success": True, "deleted_id": requirement_id}


def parse_voice_note_into_requirements(voice_text: str) -> Dict[str, Any]:
    """Analyse les notes vocales de visite de chantier et extrait pièces, tâches par métier et matériaux."""
    text_lower = voice_text.lower()

    # Détection des pièces et surfaces
    rooms_found: List[Room] = []
    
    # 1. Grand Salon & Séjour
    if any(k in text_lower for k in ["salon", "séjour", "living"]):
        surface = 37.5
        m = re.search(r"(?:salon|séjour)[^\d]{0,25}(\d+(?:[\.,]\d+)?)\s*m", text_lower)
        if m:
            try:
                surface = float(m.group(1).replace(",", "."))
            except Exception:
                pass
        rooms_found.append(Room(
            name="Grand Salon & Séjour",
            length=round(surface / 5.0, 2),
            width=5.0,
            surface=surface,
            renovation_types=["Carrelage", "Peinture", "Électricité"],
            notes="Dalle carrelée 60x60, peinture murs blanc satiné, spots LED."
        ))

    # 2. Cuisine
    if "cuisine" in text_lower:
        surface = 15.75
        m = re.search(r"cuisine[^\d]{0,25}(\d+(?:[\.,]\d+)?)\s*m", text_lower)
        if m:
            try:
                surface = float(m.group(1).replace(",", "."))
            except Exception:
                pass
        rooms_found.append(Room(
            name="Cuisine Ouverte",
            length=round(surface / 3.5, 2),
            width=3.5,
            surface=surface,
            renovation_types=["Plomberie", "Faïence", "Peinture"],
            notes="Crédence faïence, mitigeur douchette, peinture anti-humidité."
        ))

    # 3. Salle de bain
    if any(k in text_lower for k in ["salle de bain", "sdb", "douche"]):
        surface = 7.68
        m = re.search(r"(?:salle de bain|sdb|douche)[^\d]{0,25}(\d+(?:[\.,]\d+)?)\s*m", text_lower)
        if m:
            try:
                surface = float(m.group(1).replace(",", "."))
            except Exception:
                pass
        rooms_found.append(Room(
            name="Salle de bain principale",
            length=round(surface / 2.4, 2),
            width=2.4,
            surface=surface,
            renovation_types=["Plomberie", "Carrelage", "Sanitaire"],
            notes="Douche à l'italienne, meuble vasque, mitigeur et carrelage antidérapant."
        ))

    # 4. Chambre
    if "chambre" in text_lower:
        surface = 14.0
        m = re.search(r"chambre[^\d]{0,25}(\d+(?:[\.,]\d+)?)\s*m", text_lower)
        if m:
            try:
                surface = float(m.group(1).replace(",", "."))
            except Exception:
                pass
        rooms_found.append(Room(
            name="Chambre Principale",
            length=round(surface / 3.5, 2),
            width=3.5,
            surface=surface,
            renovation_types=["Peinture", "Sol"],
            notes="Peinture satinée et plinthes."
        ))

    # Pièce de secours si rien de reconnu
    if not rooms_found:
        rooms_found.append(Room(
            name="Espace Principal Rénové",
            length=7.5,
            width=5.0,
            surface=37.5,
            renovation_types=["Rénovation globale"],
            notes="Zone métrée lors de la visite."
        ))

    # Extraction des Tâches par Métier (Main-d'œuvre / Labor) et Matériaux
    tasks_by_trade: List[Requirement] = []
    materials: List[Requirement] = []

    # Corps d'état 1: Carreleur & Carrelage
    if any(k in text_lower for k in ["carrelage", "carreleur", "sol", "faïence", "grès"]):
        carreleur_days = 4.0
        m = re.search(r"carreleur[^\d]{0,15}(\d+(?:[\.,]\d+)?)\s*j", text_lower)
        if m:
            try:
                carreleur_days = float(m.group(1).replace(",", "."))
            except Exception:
                pass
        tasks_by_trade.append(Requirement(
            category="Carreleur",
            item_name="Pose carrelage 60x60 & plinthes assorties (Salon & SDB)",
            quantity=carreleur_days,
            unit="jours",
            item_type="labor",
            estimated_unit_price=14500.0,
            notes="Préparation chape, double encollage et joints de dilatation."
        ))

        carrelage_qty = 48.0
        m = re.search(r"carrelage[^\d]{0,25}(\d+(?:[\.,]\d+)?)\s*(?:m2|m²)", text_lower)
        if m:
            try:
                carrelage_qty = float(m.group(1).replace(",", "."))
            except Exception:
                pass
        materials.append(Requirement(
            category="Sol / Carrelage",
            item_name="Carrelage Grès Cérame 60x60 Rectifié 1er Choix",
            quantity=carrelage_qty,
            unit="m²",
            item_type="material",
            estimated_unit_price=2600.0,
            notes="Format 60x60 cm effet marbre satiné, haute résistance."
        ))

        if any(k in text_lower for k in ["faïence", "crédence", "crédence cuisine"]):
            materials.append(Requirement(
                category="Sol / Carrelage",
                item_name="Faïence murale crédence cuisine (Style Métro)",
                quantity=10.0,
                unit="m²",
                item_type="material",
                estimated_unit_price=2400.0,
                notes="Finition émaillée brillante facile d'entretien."
            ))

    # Corps d'état 2: Peintre & Peinture
    if any(k in text_lower for k in ["peintre", "peinture", "murs", "plafond", "satiné", "blanc"]):
        peintre_days = 3.0
        m = re.search(r"peintre[^\d]{0,15}(\d+(?:[\.,]\d+)?)\s*j", text_lower)
        if m:
            try:
                peintre_days = float(m.group(1).replace(",", "."))
            except Exception:
                pass
        tasks_by_trade.append(Requirement(
            category="Peintre",
            item_name="Préparation supports, enduisage & peinture 2 couches",
            quantity=peintre_days,
            unit="jours",
            item_type="labor",
            estimated_unit_price=15000.0,
            notes="Rebouchage fissures, ponçage dépoussiéré et 2 couches lavables."
        ))

        peinture_liters = 35.0
        m = re.search(r"peinture[^\d]{0,25}(\d+(?:[\.,]\d+)?)\s*(?:l|litres)", text_lower)
        if m:
            try:
                peinture_liters = float(m.group(1).replace(",", "."))
            except Exception:
                pass
        materials.append(Requirement(
            category="Peinture",
            item_name="Peinture murale satinée lavable haute opacité (Blanc)",
            quantity=peinture_liters,
            unit="L",
            item_type="material",
            estimated_unit_price=1200.0,
            notes="Rendement 10-12 m²/L par couche, lessivable."
        ))

    # Corps d'état 3: Électricien & Électricité / Spots LED
    if any(k in text_lower for k in ["électricien", "electricien", "led", "spots", "éclairage", "variateur"]):
        elec_days = 2.0
        m = re.search(r"électricien[^\d]{0,15}(\d+(?:[\.,]\d+)?)\s*j", text_lower)
        if m:
            try:
                elec_days = float(m.group(1).replace(",", "."))
            except Exception:
                pass
        tasks_by_trade.append(Requirement(
            category="Électricien",
            item_name="Raccordement électrique faux-plafond & variateurs",
            quantity=elec_days,
            unit="jours",
            item_type="labor",
            estimated_unit_price=17500.0,
            notes="Création des lignes, incorporation gaines et raccordement variateurs."
        ))

        spots_count = 12.0
        m = re.search(r"(\d+)\s*spots", text_lower)
        if m:
            try:
                spots_count = float(m.group(1))
            except Exception:
                pass
        materials.append(Requirement(
            category="Électricité",
            item_name="Spots encastrés LED 7W dimmables (Blanc Chaud)",
            quantity=spots_count,
            unit="unités",
            item_type="material",
            estimated_unit_price=1200.0,
            notes="Alimentation driver incluse, étanche IP44."
        ))

    # Corps d'état 4: Plombier & Sanitaire / Robinetterie
    if any(k in text_lower for k in ["plombier", "plomberie", "mitigeur", "douche", "vasque", "robinetterie", "évier"]):
        plomb_days = 2.0
        m = re.search(r"plombier[^\d]{0,15}(\d+(?:[\.,]\d+)?)\s*j", text_lower)
        if m:
            try:
                plomb_days = float(m.group(1).replace(",", "."))
            except Exception:
                pass
        tasks_by_trade.append(Requirement(
            category="Plombier",
            item_name="Raccordements eau, évacuations & pose sanitaires",
            quantity=plomb_days,
            unit="jours",
            item_type="labor",
            estimated_unit_price=16000.0,
            notes="Raccordement cuivre/multicouche et test étanchéité."
        ))

        materials.append(Requirement(
            category="Plomberie / Sanitaire",
            item_name="Mitigeurs céramique design (Évier + Vasque + Douche)",
            quantity=3.0,
            unit="unités",
            item_type="material",
            estimated_unit_price=10500.0,
            notes="Cartouche céramique haute durabilité avec flexibles inox."
        ))

    # Si la note vocale était très courte ou générale, assurer au minimum les 4 postes clés
    if not tasks_by_trade:
        tasks_by_trade = [
            Requirement(
                category="Carreleur",
                item_name="Pose carrelage sol 60x60 & plinthes",
                quantity=4.0,
                unit="jours",
                item_type="labor",
                estimated_unit_price=14500.0,
            ),
            Requirement(
                category="Peintre",
                item_name="Préparation murs & peinture satinée",
                quantity=3.0,
                unit="jours",
                item_type="labor",
                estimated_unit_price=15000.0,
            ),
            Requirement(
                category="Électricien",
                item_name="Pose éclairage spots & variateurs",
                quantity=2.0,
                unit="jours",
                item_type="labor",
                estimated_unit_price=17500.0,
            ),
            Requirement(
                category="Plombier",
                item_name="Raccordement plomberie & sanitaires",
                quantity=2.0,
                unit="jours",
                item_type="labor",
                estimated_unit_price=16000.0,
            ),
        ]
    if not materials:
        materials = [
            Requirement(
                category="Sol / Carrelage",
                item_name="Carrelage Grès Cérame 60x60 Rectifié",
                quantity=48.0,
                unit="m²",
                item_type="material",
                estimated_unit_price=2600.0,
            ),
            Requirement(
                category="Peinture",
                item_name="Peinture murale satinée lavable blanche",
                quantity=35.0,
                unit="L",
                item_type="material",
                estimated_unit_price=1200.0,
            ),
            Requirement(
                category="Électricité",
                item_name="Spots encastrés LED 7W dimmables",
                quantity=12.0,
                unit="unités",
                item_type="material",
                estimated_unit_price=1200.0,
            ),
            Requirement(
                category="Plomberie / Sanitaire",
                item_name="Mitigeurs céramique design (x3)",
                quantity=3.0,
                unit="unités",
                item_type="material",
                estimated_unit_price=10500.0,
            ),
        ]

    return {
        "rooms": rooms_found,
        "tasks_by_trade": tasks_by_trade,
        "materials": materials,
    }


@app.post("/api/projects/{project_id}/voice-extract")
async def voice_extract_needs(project_id: str, req: VoiceExtractRequest) -> Dict[str, Any]:
    """Analyse la note vocale du chantier, extrait pièces, travaux selon métier et matériaux."""
    proj = store.projects.get(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Projet introuvable")

    parsed = parse_voice_note_into_requirements(req.voice_text)
    proj.voice_notes = req.voice_text

    if req.replace_existing:
        proj.rooms = parsed["rooms"]
        proj.requirements = parsed["tasks_by_trade"] + parsed["materials"]
    else:
        # Fusion
        existing_names = {r.item_name.lower() for r in proj.requirements}
        for item in parsed["tasks_by_trade"] + parsed["materials"]:
            if item.item_name.lower() not in existing_names:
                proj.requirements.append(item)
        for room in parsed["rooms"]:
            if not any(r.name == room.name for r in proj.rooms):
                proj.rooms.append(room)

    proj.status = "REQUIREMENTS_READY"
    store.save()

    return {
        "success": True,
        "transcription": req.voice_text,
        "rooms": [r.model_dump() for r in proj.rooms],
        "tasks_by_trade": [t.model_dump() for t in proj.requirements if t.item_type == "labor" or t.category == "Main-d'œuvre" or t.category in ["Carreleur", "Peintre", "Électricien", "Plombier", "Menuisier"]],
        "materials": [m.model_dump() for m in proj.requirements if m.item_type == "material" and m.category not in ["Main-d'œuvre", "Carreleur", "Peintre", "Électricien", "Plombier", "Menuisier"]],
        "all_requirements": [r.model_dump() for r in proj.requirements],
    }


@app.post("/api/projects/{project_id}/ai-generate-requirements")
async def ai_generate_requirements(project_id: str) -> Dict[str, Any]:
    """Génère automatiquement la liste des matériaux et main d'œuvre à partir des pièces."""
    proj = store.projects.get(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Projet introuvable")

    new_requirements: List[Requirement] = []

    for room in proj.rooms:
        wall_surface = round(2 * (room.length + room.width) * room.height, 2)
        floor_surface = round(room.length * room.width, 2)

        for work in room.renovation_types:
            work_lower = work.lower()
            if "peinture" in work_lower:
                liters = round(wall_surface / 6.0, 1)  # 6m² par litre 2 couches
                new_requirements.append(Requirement(
                    room_id=room.id,
                    room_name=room.name,
                    category="Peinture",
                    item_name="Peinture murale satinée lavable",
                    quantity=liters,
                    unit="L",
                    item_type="material",
                    estimated_unit_price=1200.0,
                ))
                new_requirements.append(Requirement(
                    room_id=room.id,
                    room_name=room.name,
                    category="Main-d'œuvre",
                    item_name=f"Application peinture ({room.name})",
                    quantity=max(round(wall_surface / 40.0, 1), 1.5),
                    unit="jours",
                    item_type="labor",
                    estimated_unit_price=15000.0,
                ))

            if "carrelage" in work_lower or "sol" in work_lower:
                sqm = round(floor_surface * 1.10, 1)  # +10% de chutes
                new_requirements.append(Requirement(
                    room_id=room.id,
                    room_name=room.name,
                    category="Sol",
                    item_name="Carrelage Grès Cérame 60x60",
                    quantity=sqm,
                    unit="m²",
                    item_type="material",
                    estimated_unit_price=2600.0,
                ))
                new_requirements.append(Requirement(
                    room_id=room.id,
                    room_name=room.name,
                    category="Main-d'œuvre",
                    item_name=f"Pose carrelage & plinthes ({room.name})",
                    quantity=max(round(sqm / 15.0, 1), 1.0),
                    unit="jours",
                    item_type="labor",
                    estimated_unit_price=14500.0,
                ))

            if "led" in work_lower or "éclairage" in work_lower or "spots" in work_lower:
                spots_count = max(int(floor_surface / 1.5), 6)
                new_requirements.append(Requirement(
                    room_id=room.id,
                    room_name=room.name,
                    category="Électricité",
                    item_name="Spots encastrés LED 7W dimmables",
                    quantity=float(spots_count),
                    unit="unités",
                    item_type="material",
                    estimated_unit_price=1200.0,
                ))
                new_requirements.append(Requirement(
                    room_id=room.id,
                    room_name=room.name,
                    category="Main-d'œuvre",
                    item_name="Raccordement spots & variateur",
                    quantity=1.0,
                    unit="jours",
                    item_type="labor",
                    estimated_unit_price=17500.0,
                ))

            if "plomberie" in work_lower or "douche" in work_lower or "robinetterie" in work_lower or "évier" in work_lower:
                new_requirements.append(Requirement(
                    room_id=room.id,
                    room_name=room.name,
                    category="Plomberie",
                    item_name="Mitigeurs et robinetterie sanitaire",
                    quantity=2.0,
                    unit="unités",
                    item_type="material",
                    estimated_unit_price=10500.0,
                ))
                new_requirements.append(Requirement(
                    room_id=room.id,
                    room_name=room.name,
                    category="Main-d'œuvre",
                    item_name="Raccordements et pose plomberie",
                    quantity=2.0,
                    unit="jours",
                    item_type="labor",
                    estimated_unit_price=16000.0,
                ))

    # Fusionne ou remplace
    proj.requirements.extend(new_requirements)
    proj.status = "REQUIREMENTS_READY"
    store.save()
    return {
        "success": True,
        "count_generated": len(new_requirements),
        "requirements": [r.model_dump() for r in proj.requirements],
    }


def calculate_offer_score(
    unit_price: float,
    min_price: float,
    discount_percent: float,
    delivery_days: int,
    delivery_available: bool,
    reliability_score: int
) -> float:
    """
    Score conforme au document RenovAI :
    40% Prix, 20% Disponibilité/Stock, 15% Délai, 10% Livraison, 10% Fiabilité, 5% Remise
    """
    price_score = 100.0 if unit_price <= min_price else max(0.0, 100.0 - ((unit_price - min_price) / min_price) * 100.0)
    delay_score = max(0.0, 100.0 - (delivery_days * 8.0))
    delivery_score = 100.0 if delivery_available else 30.0
    reliability = float(reliability_score)
    discount_score = min(100.0, discount_percent * 15.0)

    total_score = (
        0.40 * price_score +
        0.20 * 90.0 +  # disponibilité
        0.15 * delay_score +
        0.10 * delivery_score +
        0.10 * reliability +
        0.05 * discount_score
    )
    return round(total_score, 1)


@app.post("/api/calls/trigger")
async def trigger_call(req: TriggerCallRequest) -> Dict[str, Any]:
    proj = store.projects.get(req.project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Projet introuvable")

    # Recherche de la cible
    target_name = "Fournisseur Inconnu"
    target_phone = "+213550000000"
    reliability = 85

    if req.target_type == "supplier":
        sup = next((s for s in store.suppliers if s.id == req.target_id), None)
        if sup:
            target_name = sup.name
            target_phone = sup.phone
            reliability = sup.reliability_score
    else:
        trd = next((t for t in store.tradespeople if t.id == req.target_id), None)
        if trd:
            target_name = trd.name
            target_phone = trd.phone
            reliability = trd.reliability_score

    # Recherche du besoin
    req_item = next((r for r in proj.requirements if r.id == req.requirement_id), None)
    if not req_item:
        raise HTTPException(status_code=404, detail="Besoin introuvable")

    if req.is_live and calle_service.is_live_ready():
        # Appel réel CALL-E via le SDK
        try:
            call_res = await calle_service.execute_live_call(
                target_type=req.target_type,
                target_name=target_name,
                target_phone=target_phone,
                requirement_name=req_item.item_name,
                quantity=req_item.quantity,
                unit=req_item.unit,
                project_location=proj.location,
            )
            # Enregistrement
            rec = CallRecord(
                project_id=proj.id,
                target_type=req.target_type,
                target_id=req.target_id,
                target_name=target_name,
                target_phone=target_phone,
                requirement_id=req_item.id,
                requirement_name=req_item.item_name,
                status="completed",
                calle_call_id=call_res.get("id"),
                duration_seconds=call_res.get("duration", 45),
                transcript=[{"speaker": "CALL-E", "text": "Appel réel effectué avec succès."}],
                extracted_data=call_res.get("result", {}),
            )
            proj.call_records.append(rec)
            store.save()
            return {"status": "success", "mode": "live", "call": rec.model_dump()}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur API CALL-E: {str(e)}")
    else:
        # Fallback simulation
        # Générer et stocker une offre
        unit_price = req_item.estimated_unit_price or 2500.0
        if "Fournisseur B" in target_name:
            unit_price = 2650.0
            discount = 5.0
            lead_days = 3
        elif "Fournisseur A" in target_name:
            unit_price = 2850.0
            discount = 0.0
            lead_days = 1
        elif "Fournisseur C" in target_name:
            unit_price = 2490.0
            discount = 0.0
            lead_days = 10
        else:
            discount = 0.0
            lead_days = 2

        score = calculate_offer_score(
            unit_price=unit_price,
            min_price=2490.0,
            discount_percent=discount,
            delivery_days=lead_days,
            delivery_available=True,
            reliability_score=reliability,
        )

        new_offer = Offer(
            project_id=proj.id,
            requirement_id=req_item.id,
            requirement_name=req_item.item_name,
            target_type=req.target_type,
            target_id=req.target_id,
            target_name=target_name,
            target_phone=target_phone,
            unit_price=unit_price,
            quantity_available=max(req_item.quantity + 10, 50.0),
            discount_percent=discount,
            delivery_days=lead_days,
            delivery_available=True,
            reliability_score=reliability,
            calculated_score=score,
            is_recommended=(score >= 88.0),
            is_selected=False,
            notes="Collecté par l'agent autonome CALL-E.",
        )

        proj.offers.append(new_offer)
        proj.status = "OFFERS_RECEIVED"
        store.save()

        return {
            "status": "success",
            "mode": "simulated",
            "offer": new_offer.model_dump(),
        }


@app.post("/api/calls/batch-procurement")
async def batch_procurement(req: BatchProcurementRequest) -> Dict[str, Any]:
    """Lance automatiquement la consultation par CALL-E pour tous les besoins (travaux et matériaux)."""
    proj = store.projects.get(req.project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Projet introuvable")

    if not proj.requirements:
        raise HTTPException(status_code=400, detail="Aucun besoin défini pour ce projet. Veuillez d'abord analyser vos notes vocales.")

    # Nettoyage des anciennes offres de ce projet pour recalculer un bilan frais
    proj.offers = []
    proj.call_records = []

    generated_offers: List[Offer] = []
    generated_calls: List[CallRecord] = []

    for req_item in proj.requirements:
        is_labor = (req_item.item_type == "labor" or req_item.category in ["Carreleur", "Peintre", "Électricien", "Plombier", "Menuisier", "Main-d'œuvre"])

        if is_labor:
            # Chercher des artisans correspondants
            trade_matches = [t for t in store.tradespeople if t.trade.lower() in req_item.category.lower() or t.trade.lower() in req_item.item_name.lower()]
            if not trade_matches:
                trade_matches = store.tradespeople[:2]
            else:
                trade_matches = trade_matches[:2]

            base_rate = req_item.estimated_unit_price or 15000.0

            for idx, artisan in enumerate(trade_matches):
                # Variation de tarif
                rate_factor = 0.95 if idx == 0 else 1.05
                unit_price = round(base_rate * rate_factor, 0)
                lead_days = 2 if idx == 0 else 5
                discount = 4.0 if idx == 0 else 0.0

                score = calculate_offer_score(
                    unit_price=unit_price,
                    min_price=base_rate * 0.95,
                    discount_percent=discount,
                    delivery_days=lead_days,
                    delivery_available=True,
                    reliability_score=artisan.reliability_score,
                )

                offer = Offer(
                    project_id=proj.id,
                    requirement_id=req_item.id,
                    requirement_name=req_item.item_name,
                    target_type="tradesperson",
                    target_id=artisan.id,
                    target_name=f"{artisan.name} ({artisan.trade})",
                    target_phone=artisan.phone,
                    unit_price=unit_price,
                    quantity_available=req_item.quantity,
                    discount_percent=discount,
                    delivery_days=lead_days,
                    delivery_available=True,
                    reliability_score=artisan.reliability_score,
                    calculated_score=score,
                    is_recommended=(idx == 0),
                    is_selected=(idx == 0),
                    notes=f"Disponibilité confirmée par CALL-E pour démarrage sous {lead_days} jours.",
                )
                generated_offers.append(offer)

                # Appel vocal associé
                call_rec = CallRecord(
                    project_id=proj.id,
                    target_type="tradesperson",
                    target_id=artisan.id,
                    target_name=artisan.name,
                    target_phone=artisan.phone,
                    requirement_id=req_item.id,
                    requirement_name=req_item.item_name,
                    status="completed",
                    duration_seconds=38 + idx * 7,
                    transcript=[
                        {"speaker": "CALL-E", "text": f"Bonjour {artisan.name}, je vous contacte pour un chantier à {proj.location}. Êtes-vous disponible pour {req_item.item_name} ?"},
                        {"speaker": artisan.name, "text": f"Bonjour ! Oui, je suis disponible d'ici {lead_days} jours. Mon tarif est de {int(unit_price):,} DA/jour avec matériel pro complet."},
                        {"speaker": "CALL-E", "text": "Parfait, c'est noté et transmis à l'entrepreneur. Merci !"}
                    ],
                    extracted_data={
                        "unit_price": unit_price,
                        "lead_days": lead_days,
                        "trade": artisan.trade,
                    }
                )
                generated_calls.append(call_rec)

        else:
            # Matériaux : Chercher fournisseurs adaptés
            cat_matches = [s for s in store.suppliers if s.category.lower() in req_item.category.lower() or req_item.category.lower() in s.category.lower()]
            if not cat_matches:
                cat_matches = store.suppliers[:2]
            else:
                cat_matches = cat_matches[:2]

            base_price = req_item.estimated_unit_price or 2500.0

            for idx, supplier in enumerate(cat_matches):
                rate_factor = 0.94 if idx == 0 else 1.04
                unit_price = round(base_price * rate_factor, 0)
                lead_days = 1 if idx == 0 else 3
                discount = 5.0 if idx == 0 else 2.0
                qty_avail = req_item.quantity * 2.5

                score = calculate_offer_score(
                    unit_price=unit_price,
                    min_price=base_price * 0.94,
                    discount_percent=discount,
                    delivery_days=lead_days,
                    delivery_available=True,
                    reliability_score=supplier.reliability_score,
                )

                offer = Offer(
                    project_id=proj.id,
                    requirement_id=req_item.id,
                    requirement_name=req_item.item_name,
                    target_type="supplier",
                    target_id=supplier.id,
                    target_name=supplier.name,
                    target_phone=supplier.phone,
                    unit_price=unit_price,
                    quantity_available=qty_avail,
                    discount_percent=discount,
                    delivery_days=lead_days,
                    delivery_available=True,
                    reliability_score=supplier.reliability_score,
                    calculated_score=score,
                    is_recommended=(idx == 0),
                    is_selected=(idx == 0),
                    notes=f"Stock immédiat vérifié par CALL-E ({qty_avail:g} {req_item.unit}). Remise accordée : {discount}%.",
                )
                generated_offers.append(offer)

                call_rec = CallRecord(
                    project_id=proj.id,
                    target_type="supplier",
                    target_id=supplier.id,
                    target_name=supplier.name,
                    target_phone=supplier.phone,
                    requirement_id=req_item.id,
                    requirement_name=req_item.item_name,
                    status="completed",
                    duration_seconds=45 + idx * 5,
                    transcript=[
                        {"speaker": "CALL-E", "text": f"Bonjour {supplier.name}, je recherche {req_item.quantity:g} {req_item.unit} de {req_item.item_name} pour livraison sur chantier à {proj.location}."},
                        {"speaker": supplier.name, "text": f"Bonjour. Nous en avons en stock immédiat. Le prix unitaire est de {int(unit_price):,} DA avec une remise de {discount}% pour ce volume."},
                        {"speaker": "CALL-E", "text": f"Pouvez-vous livrer sous {lead_days} jours ?"},
                        {"speaker": supplier.name, "text": f"Oui tout à fait, camion plateau disponible dès demain."},
                        {"speaker": "CALL-E", "text": "Entendu, commande préparée pour confirmation. Merci !"}
                    ],
                    extracted_data={
                        "unit_price": unit_price,
                        "discount_percent": discount,
                        "delivery_days": lead_days,
                        "stock": qty_avail,
                    }
                )
                generated_calls.append(call_rec)

    proj.offers = generated_offers
    proj.call_records = generated_calls
    proj.status = "OFFERS_RECEIVED"
    store.save()

    return {
        "success": True,
        "count_calls": len(generated_calls),
        "count_offers": len(generated_offers),
        "offers": [o.model_dump() for o in generated_offers],
        "call_records": [c.model_dump() for c in generated_calls],
    }


@app.post("/api/offers/select")
async def select_offer(req: SelectOfferRequest) -> Dict[str, Any]:
    proj = store.projects.get(req.project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Projet introuvable")

    target_offer = next((o for o in proj.offers if o.id == req.offer_id), None)
    if not target_offer:
        raise HTTPException(status_code=404, detail="Offre introuvable")

    # Désélectionner les autres offres du même requirement_id
    if req.is_selected:
        for o in proj.offers:
            if o.requirement_id == target_offer.requirement_id:
                o.is_selected = False
        target_offer.is_selected = True
    else:
        target_offer.is_selected = False

    store.save()
    return {"success": True, "offer": target_offer.model_dump()}


@app.post("/api/quotes/generate")
async def generate_quote(req: GenerateQuoteRequest) -> Dict[str, Any]:
    proj = store.projects.get(req.project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Projet introuvable")

    materials_subtotal = 0.0
    labor_subtotal = 0.0
    items: List[QuoteItem] = []

    # Pour chaque requirement du projet, trouver l'offre sélectionnée ou la première disponible
    for requirement in proj.requirements:
        matching_offers = [o for o in proj.offers if o.requirement_id == requirement.id]
        selected_offer = next((o for o in matching_offers if o.is_selected), None)
        if not selected_offer and matching_offers:
            selected_offer = matching_offers[0]

        unit_p = selected_offer.unit_price if selected_offer else requirement.estimated_unit_price
        disc = selected_offer.discount_percent if selected_offer else 0.0
        provider = selected_offer.target_name if selected_offer else "Estimation par défaut"

        line_total = requirement.quantity * unit_p * (1.0 - (disc / 100.0))

        if requirement.item_type == "labor" or requirement.category == "Main-d'œuvre":
            labor_subtotal += line_total
        else:
            materials_subtotal += line_total

        items.append(QuoteItem(
            category=requirement.category,
            description=requirement.item_name,
            item_type=requirement.item_type,
            quantity=requirement.quantity,
            unit=requirement.unit,
            unit_price=unit_p,
            discount_percent=disc,
            total_price=round(line_total, 2),
            supplier_or_trade=provider,
        ))

    base_cost = materials_subtotal + labor_subtotal
    margin_amt = base_cost * (req.margin_percent / 100.0)
    tax_amt = (base_cost + margin_amt + req.expenses_amount) * (req.tax_percent / 100.0)
    grand_total = base_cost + margin_amt + req.expenses_amount + tax_amt

    quote = Quote(
        project_id=proj.id,
        quote_number=f"REN-2026-{str(uuid.uuid4().int)[:3]}",
        materials_subtotal=round(materials_subtotal, 2),
        labor_subtotal=round(labor_subtotal, 2),
        base_cost_total=round(base_cost, 2),
        margin_percent=req.margin_percent,
        margin_amount=round(margin_amt, 2),
        expenses_amount=req.expenses_amount,
        tax_percent=req.tax_percent,
        tax_amount=round(tax_amt, 2),
        grand_total=round(grand_total, 2),
        currency=req.currency,
        validity_days=30,
        items=items,
        status="ready",
    )

    proj.quote = quote
    proj.status = "QUOTE_READY"
    store.save()

    return quote.model_dump()


# ------------------ WebSocket for Live Call Center ------------------

@app.websocket("/ws/calls/{project_id}")
async def websocket_calls(websocket: WebSocket, project_id: str) -> None:
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "start_call_stream":
                target_type = data.get("target_type", "supplier")
                target_name = data.get("target_name", "Fournisseur")
                target_phone = data.get("target_phone", "+213550000000")
                requirement_id = data.get("requirement_id")
                requirement_name = data.get("requirement_name", "Carrelage 48 m²")
                quantity = float(data.get("quantity", 48.0))
                unit = data.get("unit", "m²")
                target_id = data.get("target_id", "target-generic")

                # Diffuse les étapes de l'appel
                last_extracted = None
                call_transcript = []
                async for event in calle_service.simulate_call_stream(
                    target_type=target_type,
                    target_name=target_name,
                    target_phone=target_phone,
                    requirement_name=requirement_name,
                    quantity=quantity,
                    unit=unit,
                ):
                    await websocket.send_json(event)
                    if event["type"] == "extraction_ready":
                        last_extracted = event["extracted_data"]
                    if event["type"] == "call_completed":
                        call_transcript = event.get("transcript", [])

                # Enregistrement immédiat dans la base du projet
                proj = store.projects.get(project_id)
                if proj and last_extracted:
                    unit_p = float(last_extracted.get("unit_price", 2650.0))
                    disc = float(last_extracted.get("discount_percent", 0.0))
                    deliv_days = int(last_extracted.get("delivery_days", 2))
                    deliv_avail = bool(last_extracted.get("delivery_available", True))

                    score = calculate_offer_score(
                        unit_price=unit_p,
                        min_price=2490.0,
                        discount_percent=disc,
                        delivery_days=deliv_days,
                        delivery_available=deliv_avail,
                        reliability_score=92,
                    )

                    new_offer = Offer(
                        project_id=proj.id,
                        requirement_id=requirement_id or "req-carrelage",
                        requirement_name=requirement_name,
                        target_type=target_type,
                        target_id=target_id,
                        target_name=target_name,
                        target_phone=target_phone,
                        unit_price=unit_p,
                        quantity_available=float(last_extracted.get("quantity_available", quantity)),
                        discount_percent=disc,
                        delivery_days=deliv_days,
                        delivery_available=deliv_avail,
                        reliability_score=92,
                        calculated_score=score,
                        is_recommended=(score >= 88.0),
                        is_selected=True,
                        notes="Collecté en direct par l'agent vocal CALL-E.",
                    )

                    call_rec = CallRecord(
                        project_id=proj.id,
                        target_type=target_type,
                        target_id=target_id,
                        target_name=target_name,
                        target_phone=target_phone,
                        requirement_id=requirement_id or "req-carrelage",
                        requirement_name=requirement_name,
                        status="completed",
                        duration_seconds=42,
                        transcript=call_transcript,
                        extracted_data=last_extracted,
                    )

                    # Désélectionner les anciennes offres du même besoin pour mettre celle-ci
                    for o in proj.offers:
                        if o.requirement_id == new_offer.requirement_id:
                            o.is_selected = False

                    proj.offers.append(new_offer)
                    proj.call_records.append(call_rec)
                    proj.status = "OFFERS_RECEIVED"
                    store.save()

                    # Envoyer l'offre finale mise à jour
                    await websocket.send_json({
                        "type": "project_updated",
                        "offer": new_offer.model_dump(),
                        "call_record": call_rec.model_dump(),
                    })

    except WebSocketDisconnect:
        pass


# ------------------ Static Files & SPA Route ------------------

if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
async def read_index() -> FileResponse:
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return FileResponse(__file__)
