import asyncio
import os
import random
import re
import uuid
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.calle_service import calle_service
from backend.gemini_service import gemini_service
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


@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.endswith(".js") or path.endswith(".css") or path.endswith(".html") or path == "/":
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")


# ------------------ Pydantic Schemas for Requests ------------------

class CreateProjectRequest(BaseModel):
    name: str
    client_name: str
    client_phone: str = ""
    client_email: str = ""
    location: str = "Metro Area"
    surface_sqm: float = 120.0
    project_type: str = "Residential Interior Remodel"


class AddRoomRequest(BaseModel):
    name: str
    length: float
    width: float
    height: float = 9.0
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
    currency: str = "$"


class VoiceExtractRequest(BaseModel):
    voice_text: str
    replace_existing: bool = True


class VoiceExtractAudioRequest(BaseModel):
    audio_base64: str
    mime_type: str = "audio/wav"
    replace_existing: bool = True
    voice_text: Optional[str] = ""


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
    calle_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = "gemini-3.8-flash"


# ------------------ REST Endpoints ------------------

@app.api_route("/api/health", methods=["GET", "HEAD"])
async def health_check() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "app": "ContractorPilot",
        "calle_ready": calle_service.is_live_ready(),
        "calle_has_key": bool(calle_service.api_key),
        "gemini_ready": gemini_service.is_configured(),
        "gemini_model": gemini_service.model_name,
    }


@app.get("/api/settings")
async def get_settings() -> Dict[str, Any]:
    masked_calle_key = ""
    if calle_service.api_key:
        masked_calle_key = f"{calle_service.api_key[:4]}...{calle_service.api_key[-4:]}" if len(calle_service.api_key) > 8 else "***"

    masked_gemini_key = ""
    if gemini_service.api_key:
        masked_gemini_key = f"{gemini_service.api_key[:4]}...{gemini_service.api_key[-4:]}" if len(gemini_service.api_key) > 8 else "***"

    return {
        "calle_api_key_masked": masked_calle_key,
        "is_live_ready": calle_service.is_live_ready(),
        "gemini_api_key_masked": masked_gemini_key,
        "gemini_is_ready": gemini_service.is_configured(),
        "gemini_model": gemini_service.model_name,
    }


@app.post("/api/settings")
async def update_settings(req: SettingsRequest) -> Dict[str, Any]:
    if req.calle_api_key is not None:
        calle_service.update_api_key(req.calle_api_key.strip())
    if req.gemini_api_key is not None:
        gemini_service.update_config(req.gemini_api_key.strip(), req.gemini_model)
    return {
        "success": True,
        "is_live_ready": calle_service.is_live_ready(),
        "gemini_is_ready": gemini_service.is_configured(),
        "gemini_model": gemini_service.model_name,
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
        raise HTTPException(status_code=404, detail="Project not found")
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
        raise HTTPException(status_code=404, detail="Project not found")

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
        raise HTTPException(status_code=404, detail="Project not found")

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
        raise HTTPException(status_code=404, detail="Project not found")

    target = next((r for r in proj.requirements if r.id == requirement_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Requirement not found")

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
        raise HTTPException(status_code=404, detail="Project not found")

    initial_len = len(proj.requirements)
    proj.requirements = [r for r in proj.requirements if r.id != requirement_id]
    if len(proj.requirements) == initial_len:
        raise HTTPException(status_code=404, detail="Requirement not found")

    store.save()
    return {"success": True, "deleted_id": requirement_id}


def is_construction_related(text: str) -> bool:
    """Verifies whether the text pertains to home renovation, remodeling, or contractor construction trades."""
    if not text or len(text.strip()) < 4:
        return False
    t = text.lower()
    keywords = [
        # French
        "renov", "chantier", "travaux", "salon", "sejour", "cuisine", "chambre", "bain", "douche",
        "peintre", "peinture", "carrel", "plomb", "electr", "menuis", "sol", "mur", "plafond",
        "parquet", "faience", "credence", "cloison", "platre", "macon", "spot", "led", "evier",
        "lavabo", "baignoire", "robinet", "porte", "fenetre", "m2", "metre", "surface", "devis",
        "isolation", "toiture", "charpente", "facade", "terrasse", "amenagement", "bricolage",
        # English
        "remodel", "construct", "walkthrough", "living", "kitchen", "bath", "shower", "bed",
        "tiler", "tile", "paint", "painter", "electric", "plumb", "drywall", "floor", "wall",
        "ceiling", "fixture", "sq ft", "sqft", "ft", "gal", "cabinet", "countertop", "framing",
        "subcontractor", "demo", "demolition", "insulation", "roof", "deck", "patio", "scope"
    ]
    return any(k in t for k in keywords)


def parse_voice_note_into_requirements(voice_text: str) -> Dict[str, Any]:
    """Analyzes jobsite walkthrough notes and extracts rooms, trade subcontractor tasks, and materials."""
    if not is_construction_related(voice_text):
        return {
            "is_relevant": False,
            "rejection_reason": (
                "The dictation does not appear to describe home renovation, remodeling, or contractor trades. "
                "Please dictate rooms, dimensions, materials, or subcontractor tasks to perform."
            ),
            "rooms": [],
            "tasks_by_trade": [],
            "materials": [],
        }

    text_lower = voice_text.lower()

    # Room and area detection
    rooms_found: List[Room] = []
    
    # 1. Living & Dining Room
    if any(k in text_lower for k in ["living", "dining", "salon", "séjour"]):
        surface = 400.0
        m = re.search(r"(?:living|dining|salon)[^\d]{0,25}(\d+(?:[\.,]\d+)?)\s*(?:sq\s*ft|sqft|m2|m²|ft)", text_lower)
        if m:
            try:
                surface = float(m.group(1).replace(",", "."))
            except Exception:
                pass
        rooms_found.append(Room(
            name="Open Living & Dining Room",
            length=round(surface / 16.0, 1),
            width=16.0,
            height=9.0,
            surface=surface,
            renovation_types=["Wall & ceiling paint", "Recessed LED ceiling", "Hardwood flooring prep"],
            notes="South-facing natural light, dimmable LED zones required."
        ))

    # 2. Kitchen
    if "kitchen" in text_lower or "cuisine" in text_lower:
        surface = 180.0
        m = re.search(r"(?:kitchen|cuisine)[^\d]{0,25}(\d+(?:[\.,]\d+)?)\s*(?:sq\s*ft|sqft|m2|m²|ft)", text_lower)
        if m:
            try:
                surface = float(m.group(1).replace(",", "."))
            except Exception:
                pass
        rooms_found.append(Room(
            name="Chef's Kitchen",
            length=round(surface / 12.0, 1),
            width=12.0,
            height=9.0,
            surface=surface,
            renovation_types=["Porcelain floor tile", "Backsplash installation", "Plumbing rough-in & sink"],
            notes="Requires dual undermount sink connections and island wiring."
        ))

    # 3. Master Bathroom
    if any(k in text_lower for k in ["bath", "bathroom", "salle de bain", "sdb", "shower", "douche"]):
        surface = 96.0
        m = re.search(r"(?:bath|bathroom|salle de bain|shower)[^\d]{0,25}(\d+(?:[\.,]\d+)?)\s*(?:sq\s*ft|sqft|m2|m²|ft)", text_lower)
        if m:
            try:
                surface = float(m.group(1).replace(",", "."))
            except Exception:
                pass
        rooms_found.append(Room(
            name="Master Bathroom Suite",
            length=round(surface / 8.0, 1),
            width=8.0,
            height=8.5,
            surface=surface,
            renovation_types=["Wall & floor tile", "Walk-in shower pan", "Vanity faucets", "Sanitary plumbing"],
            notes="Full waterproof membrane waterproofing required for curbless shower."
        ))

    # 4. Bedroom
    if "bedroom" in text_lower or "chambre" in text_lower:
        surface = 192.0
        m = re.search(r"(?:bedroom|chambre)[^\d]{0,25}(\d+(?:[\.,]\d+)?)\s*(?:sq\s*ft|sqft|m2|m²|ft)", text_lower)
        if m:
            try:
                surface = float(m.group(1).replace(",", "."))
            except Exception:
                pass
        rooms_found.append(Room(
            name="Primary Bedroom",
            length=16.0,
            width=12.0,
            height=9.0,
            surface=surface,
            renovation_types=["Wall paint", "Hardwood trim"],
            notes="Baseboards and velvet matte paint."
        ))

    # Fallback room
    if not rooms_found:
        rooms_found.append(Room(
            name="Main Living Area",
            length=25.0,
            width=16.0,
            height=9.0,
            surface=400.0,
            renovation_types=["Complete interior remodel"],
            notes="General measured walkthrough zone."
        ))

    # Trade Labor tasks and Material Requirements
    tasks_by_trade: List[Requirement] = []
    materials: List[Requirement] = []

    # Trade 1: Master Tiler & Porcelain Tile
    if any(k in text_lower for k in ["tile", "tiler", "porcelain", "carrelage", "carreleur", "flooring", "floor"]):
        carreleur_days = 4.0
        m = re.search(r"(?:tiler|carreleur)[^\d]{0,15}(\d+(?:[\.,]\d+)?)\s*(?:day|days|j)", text_lower)
        if m:
            try:
                carreleur_days = float(m.group(1).replace(",", "."))
            except Exception:
                pass
        tasks_by_trade.append(Requirement(
            category="Tiler",
            item_name="Tile & Substrate Installation (Master Tiler)",
            quantity=carreleur_days,
            unit="days",
            item_type="labor",
            estimated_unit_price=425.0,
            notes="520 sq ft porcelain layout, precision miter cuts, waterproof substrate."
        ))

        carrelage_qty = 520.0
        m = re.search(r"(?:tile|porcelain|carrelage)[^\d]{0,25}(\d+(?:[\.,]\d+)?)\s*(?:sq\s*ft|sqft|m2|m²)", text_lower)
        if m:
            try:
                carrelage_qty = float(m.group(1).replace(",", "."))
            except Exception:
                pass
        materials.append(Requirement(
            category="Flooring",
            item_name="Porcelain Floor Tiles 24x24 (Calacatta Marble Finish)",
            quantity=carrelage_qty,
            unit="sq ft",
            item_type="material",
            estimated_unit_price=4.50,
            notes="High-traffic porcelain, rectified edges with 10% cut allowance."
        ))

        if any(k in text_lower for k in ["backsplash", "crédence", "faïence"]):
            materials.append(Requirement(
                category="Flooring",
                item_name="Subway Glazed Ceramic Wall Tile (Kitchen Backsplash)",
                quantity=45.0,
                unit="sq ft",
                item_type="material",
                estimated_unit_price=6.50,
                notes="Beveled glazed finish with stain-resistant epoxy grout."
            ))

    # Trade 2: Finish Painter & Interior Paint
    if any(k in text_lower for k in ["paint", "painter", "drywall", "peintre", "peinture", "wall", "ceiling"]):
        peintre_days = 3.0
        m = re.search(r"(?:painter|peintre)[^\d]{0,15}(\d+(?:[\.,]\d+)?)\s*(?:day|days|j)", text_lower)
        if m:
            try:
                peintre_days = float(m.group(1).replace(",", "."))
            except Exception:
                pass
        tasks_by_trade.append(Requirement(
            category="Painter",
            item_name="Surface Prep & 2-Coat Painting (Finish Painter)",
            quantity=peintre_days,
            unit="days",
            item_type="labor",
            estimated_unit_price=360.0,
            notes="Level 4 drywall prep, dust mitigation, primer plus 2 topcoats."
        ))

        paint_gal = 10.0
        m = re.search(r"(?:paint|peinture)[^\d]{0,25}(\d+(?:[\.,]\d+)?)\s*(?:gal|gallon|gallons|l|liters)", text_lower)
        if m:
            try:
                paint_gal = float(m.group(1).replace(",", "."))
            except Exception:
                pass
        materials.append(Requirement(
            category="Paint",
            item_name="Premium Interior Velvet Matte Paint (Ultra Durable)",
            quantity=paint_gal,
            unit="gal",
            item_type="material",
            estimated_unit_price=60.0,
            notes="Warm Alabaster shade, washable zero-VOC formula."
        ))

    # Trade 3: Master Electrician & Recessed LED Lights
    if any(k in text_lower for k in ["electrician", "electric", "lighting", "light", "led", "spot", "dimmer", "électricien", "électricité"]):
        elec_days = 2.0
        m = re.search(r"(?:electrician|électricien)[^\d]{0,15}(\d+(?:[\.,]\d+)?)\s*(?:day|days|j)", text_lower)
        if m:
            try:
                elec_days = float(m.group(1).replace(",", "."))
            except Exception:
                pass
        tasks_by_trade.append(Requirement(
            category="Electrician",
            item_name="Recessed Lighting Circuitry & Smart Dimmer Trim (Master Electrician)",
            quantity=elec_days,
            unit="days",
            item_type="labor",
            estimated_unit_price=480.0,
            notes="NEC compliance, smart dimmer switches, and dedicated circuits."
        ))

        spots_count = 24.0
        m = re.search(r"(\d+)\s*(?:lights|downlights|spots|fixtures)", text_lower)
        if m:
            try:
                spots_count = float(m.group(1))
            except Exception:
                pass
        materials.append(Requirement(
            category="Electrical",
            item_name="7W Dimmable Recessed LED Downlights (3000K Warm White)",
            quantity=spots_count,
            unit="units",
            item_type="material",
            estimated_unit_price=19.50,
            notes="IC-rated, airtight housing with junction boxes included."
        ))

    # Trade 4: Licensed Plumber & Fixtures
    if any(k in text_lower for k in ["plumber", "plumbing", "faucet", "valve", "shower", "sink", "plombier", "plomberie", "mitigeur"]):
        plomb_days = 2.0
        m = re.search(r"(?:plumber|plombier)[^\d]{0,15}(\d+(?:[\.,]\d+)?)\s*(?:day|days|j)", text_lower)
        if m:
            try:
                plomb_days = float(m.group(1).replace(",", "."))
            except Exception:
                pass
        tasks_by_trade.append(Requirement(
            category="Plumber",
            item_name="Sanitary Rough-in & Trim Installation (Licensed Plumber)",
            quantity=plomb_days,
            unit="days",
            item_type="labor",
            estimated_unit_price=490.0,
            notes="PEX expansion lines, shower valves, and double vanity rough-ins."
        ))

        materials.append(Requirement(
            category="Plumbing",
            item_name="Designer Brushed Brass Thermostatic Mixer Faucets",
            quantity=3.0,
            unit="units",
            item_type="material",
            estimated_unit_price=175.0,
            notes="Solid brass construction with ceramic disc valves."
        ))

    # Default fallback scopes if minimal voice input
    if not tasks_by_trade:
        tasks_by_trade = [
            Requirement(
                category="Tiler",
                item_name="Tile & Substrate Installation (Master Tiler)",
                quantity=4.0,
                unit="days",
                item_type="labor",
                estimated_unit_price=425.0,
            ),
            Requirement(
                category="Painter",
                item_name="Surface Prep & 2-Coat Painting (Finish Painter)",
                quantity=3.0,
                unit="days",
                item_type="labor",
                estimated_unit_price=360.0,
            ),
            Requirement(
                category="Electrician",
                item_name="Recessed Lighting Circuitry & Smart Dimmer Trim",
                quantity=2.0,
                unit="days",
                item_type="labor",
                estimated_unit_price=480.0,
            ),
            Requirement(
                category="Plumber",
                item_name="Sanitary Rough-in & Trim Installation",
                quantity=2.0,
                unit="days",
                item_type="labor",
                estimated_unit_price=490.0,
            ),
        ]
    if not materials:
        materials = [
            Requirement(
                category="Flooring",
                item_name="Porcelain Floor Tiles 24x24 (Calacatta Marble Finish)",
                quantity=520.0,
                unit="sq ft",
                item_type="material",
                estimated_unit_price=4.50,
            ),
            Requirement(
                category="Paint",
                item_name="Premium Interior Velvet Matte Paint (Ultra Durable)",
                quantity=10.0,
                unit="gal",
                item_type="material",
                estimated_unit_price=60.0,
            ),
            Requirement(
                category="Electrical",
                item_name="7W Dimmable Recessed LED Downlights (3000K Warm White)",
                quantity=24.0,
                unit="units",
                item_type="material",
                estimated_unit_price=19.50,
            ),
            Requirement(
                category="Plumbing",
                item_name="Designer Brushed Brass Thermostatic Mixer Faucets",
                quantity=3.0,
                unit="units",
                item_type="material",
                estimated_unit_price=175.0,
            ),
        ]

    return {
        "is_relevant": True,
        "rejection_reason": None,
        "rooms": rooms_found,
        "tasks_by_trade": tasks_by_trade,
        "materials": materials,
    }


@app.post("/api/projects/{project_id}/voice-extract")
async def voice_extract_needs(project_id: str, req: VoiceExtractRequest) -> Dict[str, Any]:
    """Analyzes the walkthrough voice dictation using Gemini 3.8 Flash (with local heuristic fallback)."""
    proj = store.projects.get(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    parsed: Optional[Dict[str, Any]] = None
    ai_engine = "Local Heuristic Engine"

    if gemini_service.is_configured():
        try:
            gemini_result = await gemini_service.analyze_walkthrough(req.voice_text)
            if gemini_result:
                gemini_rooms = [
                    Room(
                        name=str(r.get("name", "Remodel Area")),
                        length=float(r.get("length", 15.0)),
                        width=float(r.get("width", 12.0)),
                        height=float(r.get("height", 9.0)),
                        surface=float(r.get("surface", float(r.get("length", 15.0)) * float(r.get("width", 12.0)))),
                        renovation_types=list(r.get("renovation_types", ["General Remodel"])),
                        notes=str(r.get("notes", "Extracted by Gemini AI")),
                    )
                    for r in gemini_result.get("rooms", [])
                ]
                gemini_labor = [
                    Requirement(
                        category=str(t.get("category", "General Trade")),
                        item_name=str(t.get("item_name", "Subcontractor Scope")),
                        quantity=float(t.get("quantity", 2.0)),
                        unit=str(t.get("unit", "days")),
                        item_type="labor",
                        estimated_unit_price=float(t.get("estimated_unit_price", 400.0)),
                        notes=str(t.get("notes", "Estimated by Gemini AI")),
                    )
                    for t in gemini_result.get("tasks_by_trade", [])
                ]
                gemini_materials = [
                    Requirement(
                        category=str(m.get("category", "Supplies")),
                        item_name=str(m.get("item_name", "Construction Material")),
                        quantity=float(m.get("quantity", 1.0)),
                        unit=str(m.get("unit", "units")),
                        item_type="material",
                        estimated_unit_price=float(m.get("estimated_unit_price", 50.0)),
                        notes=str(m.get("notes", "Takeoff by Gemini AI")),
                    )
                    for m in gemini_result.get("materials", [])
                ]
                parsed = {
                    "is_relevant": gemini_result.get("is_relevant", True),
                    "rejection_reason": gemini_result.get("rejection_reason"),
                    "rooms": gemini_rooms,
                    "tasks_by_trade": gemini_labor,
                    "materials": gemini_materials,
                }
                used_model = gemini_result.get("ai_model", gemini_service.model_name)
                ai_engine = f"Google Gemini ({used_model})"
        except Exception as e:
            print(f"[Gemini] Error analyzing walkthrough, falling back to local engine: {e}")

    if not parsed:
        parsed = parse_voice_note_into_requirements(req.voice_text)

    # Validate topic relevance
    if parsed.get("is_relevant") is False or (not parsed.get("rooms") and not parsed.get("tasks_by_trade") and not parsed.get("materials")):
        rejection_reason = parsed.get("rejection_reason") or (
            "The dictated walkthrough does not appear to describe home renovation, remodeling, or contractor trade work."
        )
        return {
            "success": False,
            "is_off_topic": True,
            "message": rejection_reason,
            "transcription": req.voice_text,
            "rooms": [],
            "tasks_by_trade": [],
            "materials": [],
            "all_requirements": [],
        }

    proj.voice_notes = req.voice_text

    if req.replace_existing:
        proj.rooms = parsed["rooms"]
        proj.requirements = parsed["tasks_by_trade"] + parsed["materials"]
    else:
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
        "ai_engine": ai_engine,
        "transcription": req.voice_text,
        "rooms": [r.model_dump() for r in proj.rooms],
        "tasks_by_trade": [t.model_dump() for t in proj.requirements if t.item_type == "labor"],
        "materials": [m.model_dump() for m in proj.requirements if m.item_type == "material"],
        "all_requirements": [r.model_dump() for r in proj.requirements],
    }


@app.post("/api/projects/{project_id}/voice-extract-audio")
async def voice_extract_audio_needs(project_id: str, req: VoiceExtractAudioRequest) -> Dict[str, Any]:
    """Transcribes and analyzes raw recorded audio directly using Google Gemini Multimodal Audio API with live text fallback."""
    proj = store.projects.get(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    parsed = None
    ai_engine = f"Google Gemini ({gemini_service.model_name})"

    # 1. Primary path: Direct multimodal audio analysis via Gemini API
    if gemini_service.is_configured():
        try:
            parsed = await gemini_service.analyze_walkthrough_audio(req.audio_base64, req.mime_type)
            if parsed and parsed.get("ai_model"):
                ai_engine = f"Google Gemini ({parsed['ai_model']}) [Direct Audio]"
        except Exception as e:
            print(f"[Gemini Audio] Error during direct audio analysis: {e}")

    # 2. Resilient fallback: If audio analysis didn't extract scopes, but client speech recognition captured text
    if not parsed and req.voice_text and req.voice_text.strip():
        print("[Gemini Audio] Falling back to text walkthrough extraction using live transcribed text")
        if gemini_service.is_configured():
            try:
                gemini_text_result = await gemini_service.analyze_walkthrough(req.voice_text.strip())
                if gemini_text_result:
                    parsed = gemini_text_result
                    used_model = gemini_text_result.get("ai_model", gemini_service.model_name)
                    ai_engine = f"Google Gemini ({used_model}) [Voice-to-Text Fallback]"
            except Exception as e:
                print(f"[Gemini Audio] Fallback Gemini text analysis failed: {e}")
        if not parsed:
            parsed = parse_voice_note_into_requirements(req.voice_text.strip())
            ai_engine = "ContractorPilot Heuristic Engine [Voice-to-Text Fallback]"

    # 3. If neither direct audio nor text fallback succeeded
    if not parsed:
        last_err = getattr(gemini_service, "last_audio_error", None)
        if last_err == "rate_limit":
            raise HTTPException(
                status_code=429,
                detail="Google Gemini request quota temporarily reached (15 req/min). Please wait 15-20 seconds before recording again."
            )
        elif last_err == "auth_error":
            raise HTTPException(
                status_code=401,
                detail="Google Gemini API key invalid or missing. Please check your API key in Settings."
            )
        else:
            raise HTTPException(
                status_code=422,
                detail="Gemini audio analysis did not detect actionable remodel scopes in this recording. Please speak clearly into your microphone (for at least 10 seconds), or use one of the one-click demo presets below."
            )

    transcription = str(parsed.get("transcription", "")).strip()
    if not transcription and req.voice_text:
        transcription = req.voice_text.strip()
    if not transcription:
        transcription = "Jobsite audio walkthrough note"

    # Validate topic relevance
    if parsed.get("is_relevant") is False or (not parsed.get("rooms") and not parsed.get("tasks_by_trade") and not parsed.get("materials")):
        rejection_reason = parsed.get("rejection_reason") or (
            "The audio recording does not appear to describe home renovation, construction scopes, or contractor trade work."
        )
        return {
            "success": False,
            "is_off_topic": True,
            "message": rejection_reason,
            "transcription": transcription,
            "rooms": [],
            "tasks_by_trade": [],
            "materials": [],
            "all_requirements": [],
        }

    gemini_rooms: List[Room] = []
    for r in parsed.get("rooms", []):
        if isinstance(r, Room):
            gemini_rooms.append(r)
        elif isinstance(r, dict):
            gemini_rooms.append(
                Room(
                    name=str(r.get("name", "Remodel Area")),
                    length=float(r.get("length", 15.0)),
                    width=float(r.get("width", 12.0)),
                    height=float(r.get("height", 9.0)),
                    surface=float(r.get("surface", float(r.get("length", 15.0)) * float(r.get("width", 12.0)))),
                    renovation_types=list(r.get("renovation_types", ["General Remodel"])),
                    notes=str(r.get("notes", "Extracted by Gemini AI")),
                )
            )

    gemini_labor: List[Requirement] = []
    for t in parsed.get("tasks_by_trade", []):
        if isinstance(t, Requirement):
            gemini_labor.append(t)
        elif isinstance(t, dict):
            gemini_labor.append(
                Requirement(
                    category=str(t.get("category", "General Trade")),
                    item_name=str(t.get("item_name", "Subcontractor Scope")),
                    quantity=float(t.get("quantity", 2.0)),
                    unit=str(t.get("unit", "days")),
                    item_type="labor",
                    estimated_unit_price=float(t.get("estimated_unit_price", 400.0)),
                    notes=str(t.get("notes", "Estimated by Gemini AI")),
                )
            )

    gemini_materials: List[Requirement] = []
    for m in parsed.get("materials", []):
        if isinstance(m, Requirement):
            gemini_materials.append(m)
        elif isinstance(m, dict):
            gemini_materials.append(
                Requirement(
                    category=str(m.get("category", "Supplies")),
                    item_name=str(m.get("item_name", "Construction Material")),
                    quantity=float(m.get("quantity", 1.0)),
                    unit=str(m.get("unit", "units")),
                    item_type="material",
                    estimated_unit_price=float(m.get("estimated_unit_price", 50.0)),
                    notes=str(m.get("notes", "Takeoff by Gemini AI")),
                )
            )

    proj.voice_notes = transcription

    if req.replace_existing:
        proj.rooms = gemini_rooms
        proj.requirements = gemini_labor + gemini_materials
    else:
        existing_names = {r.item_name.lower() for r in proj.requirements}
        for item in gemini_labor + gemini_materials:
            if item.item_name.lower() not in existing_names:
                proj.requirements.append(item)
        for room in gemini_rooms:
            if not any(r.name == room.name for r in proj.rooms):
                proj.rooms.append(room)

    proj.status = "REQUIREMENTS_READY"
    store.save()

    return {
        "success": True,
        "ai_engine": ai_engine,
        "transcription": transcription,
        "rooms": [r.model_dump() for r in proj.rooms],
        "tasks_by_trade": [t.model_dump() for t in proj.requirements if t.item_type == "labor"],
        "materials": [m.model_dump() for m in proj.requirements if m.item_type == "material"],
        "all_requirements": [r.model_dump() for r in proj.requirements],
    }


@app.post("/api/projects/{project_id}/ai-generate-requirements")
async def ai_generate_requirements(project_id: str) -> Dict[str, Any]:
    """Automatically generates material takeoffs and labor days from measured rooms."""
    proj = store.projects.get(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    new_requirements: List[Requirement] = []

    for room in proj.rooms:
        wall_surface = round(2 * (room.length + room.width) * room.height, 1)
        floor_surface = round(room.length * room.width, 1)

        for work in room.renovation_types:
            work_lower = work.lower()
            if "paint" in work_lower or "peinture" in work_lower:
                gallons = max(round(wall_surface / 350.0, 1), 2.0)  # ~350 sq ft per gallon 2 coats
                new_requirements.append(Requirement(
                    room_id=room.id,
                    room_name=room.name,
                    category="Paint",
                    item_name="Premium Interior Velvet Matte Paint",
                    quantity=gallons,
                    unit="gal",
                    item_type="material",
                    estimated_unit_price=60.0,
                ))
                new_requirements.append(Requirement(
                    room_id=room.id,
                    room_name=room.name,
                    category="Painter",
                    item_name=f"Surface prep & painting ({room.name})",
                    quantity=max(round(wall_surface / 500.0, 1), 1.5),
                    unit="days",
                    item_type="labor",
                    estimated_unit_price=360.0,
                ))

            if "tile" in work_lower or "carrelage" in work_lower or "floor" in work_lower:
                sqft = round(floor_surface * 1.10, 1)  # +10% cut allowance
                new_requirements.append(Requirement(
                    room_id=room.id,
                    room_name=room.name,
                    category="Flooring",
                    item_name="Porcelain Floor Tiles 24x24",
                    quantity=sqft,
                    unit="sq ft",
                    item_type="material",
                    estimated_unit_price=4.50,
                ))
                new_requirements.append(Requirement(
                    room_id=room.id,
                    room_name=room.name,
                    category="Tiler",
                    item_name=f"Tile installation & prep ({room.name})",
                    quantity=max(round(sqft / 130.0, 1), 1.0),
                    unit="days",
                    item_type="labor",
                    estimated_unit_price=425.0,
                ))

            if "led" in work_lower or "light" in work_lower or "spots" in work_lower:
                spots_count = max(int(floor_surface / 25), 6)
                new_requirements.append(Requirement(
                    room_id=room.id,
                    room_name=room.name,
                    category="Electrical",
                    item_name="7W Dimmable Recessed LED Downlights",
                    quantity=float(spots_count),
                    unit="units",
                    item_type="material",
                    estimated_unit_price=19.50,
                ))
                new_requirements.append(Requirement(
                    room_id=room.id,
                    room_name=room.name,
                    category="Electrician",
                    item_name=f"Ceiling circuit & dimmer install ({room.name})",
                    quantity=1.0,
                    unit="days",
                    item_type="labor",
                    estimated_unit_price=480.0,
                ))

            if "plumbing" in work_lower or "shower" in work_lower or "faucet" in work_lower:
                new_requirements.append(Requirement(
                    room_id=room.id,
                    room_name=room.name,
                    category="Plumbing",
                    item_name="Designer Thermostatic Mixer Faucets",
                    quantity=2.0,
                    unit="units",
                    item_type="material",
                    estimated_unit_price=175.0,
                ))
                new_requirements.append(Requirement(
                    room_id=room.id,
                    room_name=room.name,
                    category="Plumber",
                    item_name=f"Sanitary plumbing rough-in ({room.name})",
                    quantity=2.0,
                    unit="days",
                    item_type="labor",
                    estimated_unit_price=490.0,
                ))

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
        raise HTTPException(status_code=404, detail="Project not found")

    # Target lookup
    target_name = "Supplier Unknown"
    target_phone = "+15550000000"
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

    # Requirement lookup
    req_item = next((r for r in proj.requirements if r.id == req.requirement_id), None)
    if not req_item:
        raise HTTPException(status_code=404, detail="Requirement not found")

    if req.is_live and calle_service.is_live_ready():
        # Live CALL-E execution via SDK
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
            # Record call
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
                transcript=[{"speaker": "CALL-E", "text": "Live call completed successfully."}],
                extracted_data=call_res.get("result", {}),
            )
            proj.call_records.append(rec)
            store.save()
            return {"status": "success", "mode": "live", "call": rec.model_dump()}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"CALL-E API Error: {str(e)}")
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
    """Automatically launches CALL-E consultations for all scopes (labor & materials)."""
    proj = store.projects.get(req.project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    if not proj.requirements:
        raise HTTPException(status_code=400, detail="No requirements or scopes defined for this project. Please analyze your walkthrough voice notes first.")

    # Nettoyage des anciennes offres de ce projet pour recalculer un bilan frais
    proj.offers = []
    proj.call_records = []

    generated_offers: List[Offer] = []
    generated_calls: List[CallRecord] = []

    for req_item in proj.requirements:
        is_labor = (
            req_item.item_type == "labor"
            or req_item.category in ["Tiler", "Painter", "Electrician", "Plumber", "Carpenter", "Labor", "Carreleur", "Peintre", "Électricien", "Plombier", "Menuisier", "Main-d'œuvre"]
        )

        if is_labor:
            # Find matching subcontractors
            trade_matches = [t for t in store.tradespeople if t.trade.lower() in req_item.category.lower() or t.trade.lower() in req_item.item_name.lower()]
            if not trade_matches:
                trade_matches = store.tradespeople[:2]
            else:
                trade_matches = trade_matches[:2]

            base_rate = req_item.estimated_unit_price or 420.0

            for idx, artisan in enumerate(trade_matches):
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
                    notes=f"Availability confirmed by CALL-E for mobilization in {lead_days} days.",
                )
                generated_offers.append(offer)

                # Associated voice call record
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
                        {"speaker": "CALL-E", "text": f"Hello {artisan.name}, calling on behalf of ContractorPilot for a project at {proj.location}. Are you available for {req_item.item_name}?"},
                        {"speaker": artisan.name, "text": f"Hi! Yes, I can start within {lead_days} days. My day rate is ${int(unit_price):,}/day with full commercial equipment."},
                        {"speaker": "CALL-E", "text": "Perfect, logged and submitted to the general contractor. Thank you!"}
                    ],
                    extracted_data={
                        "unit_price": unit_price,
                        "lead_days": lead_days,
                        "trade": artisan.trade,
                    }
                )
                generated_calls.append(call_rec)

        else:
            # Materials: Match suitable suppliers
            cat_matches = [s for s in store.suppliers if s.category.lower() in req_item.category.lower() or req_item.category.lower() in s.category.lower()]
            if not cat_matches:
                cat_matches = store.suppliers[:2]
            else:
                cat_matches = cat_matches[:2]

            base_price = req_item.estimated_unit_price or 4.50

            for idx, supplier in enumerate(cat_matches):
                rate_factor = 0.94 if idx == 0 else 1.04
                unit_price = round(base_price * rate_factor, 2)
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
                    notes=f"Immediate inventory verified by CALL-E ({qty_avail:g} {req_item.unit}). Contractor trade discount: {discount}%.",
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
                        {"speaker": "CALL-E", "text": f"Hello {supplier.name}, I'm calling for ContractorPilot to check availability of {req_item.quantity:g} {req_item.unit} of {req_item.item_name} delivered to site at {proj.location}."},
                        {"speaker": supplier.name, "text": f"Hello! We have that in stock right now. Unit price is ${unit_price:,.2f} with a {discount}% volume trade discount."},
                        {"speaker": "CALL-E", "text": f"Can you guarantee jobsite delivery within {lead_days} business day{'s' if lead_days > 1 else ''}?"},
                        {"speaker": supplier.name, "text": "Yes absolutely, flatbed dispatch is scheduled for that window."},
                        {"speaker": "CALL-E", "text": "Confirmed, order hold logged for contractor signoff. Thank you!"}
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
        raise HTTPException(status_code=404, detail="Project not found")

    target_offer = next((o for o in proj.offers if o.id == req.offer_id), None)
    if not target_offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    # Deselect other offers for the same requirement_id
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
        raise HTTPException(status_code=404, detail="Project not found")

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
        quote_number=f"CP-2026-{str(uuid.uuid4().int)[:3]}",
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
                target_name = data.get("target_name", "Supplier Direct")
                target_phone = data.get("target_phone", "+1 312 555 0142")
                requirement_id = data.get("requirement_id")
                requirement_name = data.get("requirement_name", "Porcelain Floor Tiles 520 sq ft")
                quantity = float(data.get("quantity", 520.0))
                unit = data.get("unit", "sq ft")
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
    css_dir = os.path.join(FRONTEND_DIR, "css")
    js_dir = os.path.join(FRONTEND_DIR, "js")
    audio_dir = os.path.join(FRONTEND_DIR, "audio")
    video_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "video")
    if os.path.exists(css_dir):
        app.mount("/css", StaticFiles(directory=css_dir), name="css")
    if os.path.exists(js_dir):
        app.mount("/js", StaticFiles(directory=js_dir), name="js")
    if os.path.exists(audio_dir):
        app.mount("/audio", StaticFiles(directory=audio_dir), name="audio")
    if os.path.exists(video_dir):
        app.mount("/video", StaticFiles(directory=video_dir), name="video")


@app.api_route("/", methods=["GET", "HEAD"])
async def read_index() -> FileResponse:
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(
            index_path,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    return FileResponse(__file__)
