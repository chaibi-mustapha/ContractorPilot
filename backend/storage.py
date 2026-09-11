import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DATA_FILE = os.path.join(DATA_DIR, "renovai_store.json")


class Room(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    length: float  # ft or m
    width: float   # ft or m
    height: float = 9.0 # ft
    surface: float = 0.0
    renovation_types: List[str] = []
    notes: str = ""

    def model_post_init(self, __context: Any) -> None:
        if self.surface == 0.0:
            self.surface = round(self.length * self.width, 2)


class Requirement(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    room_id: Optional[str] = None
    room_name: str = ""
    category: str  # Paint, Flooring, Electrical, Plumbing, Fixtures, Carpentry, Labor
    item_name: str
    quantity: float
    unit: str  # sq ft, gal, units, days, lump sum
    item_type: str = "material"  # material | labor
    estimated_unit_price: float = 0.0
    notes: str = ""


class Supplier(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    phone: str
    category: str
    city: str
    rating: float = 4.5
    reliability_score: int = 90  # out of 100


class Tradesperson(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    phone: str
    trade: str  # Master Tiler, Finish Painter, Licensed Plumber, Master Electrician, Finish Carpenter
    city: str
    rating: float = 4.7
    reliability_score: int = 92


class Offer(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    requirement_id: str
    requirement_name: str
    target_type: str  # supplier | tradesperson
    target_id: str
    target_name: str
    target_phone: str = ""
    unit_price: float
    quantity_available: float = 0.0
    discount_percent: float = 0.0
    delivery_days: int = 2
    delivery_available: bool = True
    delivery_cost: float = 0.0
    reliability_score: int = 85
    calculated_score: float = 0.0
    is_recommended: bool = False
    is_selected: bool = False
    notes: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class CallRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    target_type: str  # supplier | tradesperson
    target_id: str
    target_name: str
    target_phone: str
    requirement_id: str
    requirement_name: str
    status: str = "completed"  # queued | calling | completed | failed | simulated
    duration_seconds: int = 42
    calle_call_id: Optional[str] = None
    transcript: List[Dict[str, str]] = []  # [{"speaker": "AI"|"Contact", "text": "..."}]
    extracted_data: Dict[str, Any] = {}
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class QuoteItem(BaseModel):
    category: str
    description: str
    item_type: str  # material | labor
    quantity: float
    unit: str
    unit_price: float
    discount_percent: float = 0.0
    total_price: float
    supplier_or_trade: str


class Quote(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    quote_number: str = "CP-2026-001"
    date_str: str = Field(default_factory=lambda: datetime.now().strftime("%b %d, %Y"))
    materials_subtotal: float = 0.0
    labor_subtotal: float = 0.0
    base_cost_total: float = 0.0
    margin_percent: float = 20.0
    margin_amount: float = 0.0
    expenses_amount: float = 0.0  # Handling/Delivery expenses
    tax_percent: float = 0.0
    tax_amount: float = 0.0
    grand_total: float = 0.0
    currency: str = "$"
    validity_days: int = 30
    items: List[QuoteItem] = []
    status: str = "ready"  # draft | ready | sent | accepted


class Project(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    client_name: str
    client_phone: str = ""
    client_email: str = ""
    location: str
    surface_sqm: float
    project_type: str = "Residential Interior Remodel"
    status: str = "SITE_VISIT"  # DRAFT | SITE_VISIT | REQUIREMENTS_READY | CALLING | OFFERS_RECEIVED | QUOTE_READY
    rooms: List[Room] = []
    requirements: List[Requirement] = []
    offers: List[Offer] = []
    call_records: List[CallRecord] = []
    voice_notes: str = ""
    quote: Optional[Quote] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# Storage Manager
class DataStore:
    def __init__(self) -> None:
        os.makedirs(DATA_DIR, exist_ok=True)
        self.suppliers: List[Supplier] = []
        self.tradespeople: List[Tradesperson] = []
        self.projects: Dict[str, Project] = {}
        self.load()

    def load(self) -> None:
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.suppliers = [Supplier(**s) for s in data.get("suppliers", [])]
                    self.tradespeople = [Tradesperson(**t) for t in data.get("tradespeople", [])]
                    self.projects = {p["id"]: Project(**p) for p in data.get("projects", [])}
                    return
            except Exception as e:
                print(f"Error loading data: {e}. Rebuilding initial seeds.")

        self.seed_defaults()
        self.save()

    def save(self) -> None:
        data = {
            "suppliers": [s.model_dump() for s in self.suppliers],
            "tradespeople": [t.model_dump() for t in self.tradespeople],
            "projects": [p.model_dump() for p in self.projects.values()],
        }
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def seed_defaults(self) -> None:
        # Default Verified Suppliers
        self.suppliers = [
            Supplier(id="sup-ceram-b", name="Apex Tile & Stone Direct (Supplier B)", phone="+1-555-019-2831", category="Tile & Flooring", city="Metro Area", rating=4.8, reliability_score=92),
            Supplier(id="sup-ceram-a", name="Grand Surface Materials (Supplier A)", phone="+1-555-019-3344", category="Tile & Flooring", city="Metro Area", rating=4.5, reliability_score=85),
            Supplier(id="sup-ceram-c", name="Atlas Porcelain Warehouse (Supplier C)", phone="+1-555-019-4455", category="Tile & Flooring", city="Metro Area", rating=4.2, reliability_score=78),
            Supplier(id="sup-peint-a", name="Sherwin ProFinish Coatings", phone="+1-555-019-5566", category="Paint & Finishes", city="Metro Area", rating=4.9, reliability_score=95),
            Supplier(id="sup-peint-b", name="ColorCraft Express Supply", phone="+1-555-019-6677", category="Paint & Finishes", city="Metro Area", rating=4.3, reliability_score=82),
            Supplier(id="sup-elec-a", name="Metro Lighting & Electric Supply", phone="+1-555-019-7788", category="Electrical & Fixtures", city="Metro Area", rating=4.7, reliability_score=90),
            Supplier(id="sup-plomb-a", name="Prestige Bath & Plumbing Fixtures", phone="+1-555-019-8899", category="Plumbing & Fixtures", city="Metro Area", rating=4.6, reliability_score=88),
        ]

        # Default Subcontractors / Tradespeople
        self.tradespeople = [
            Tradesperson(id="trade-mohamed", name="Marcus Reed (Master Tiler)", phone="+1-555-018-1122", trade="Master Tiler", city="Metro Area", rating=4.9, reliability_score=95),
            Tradesperson(id="trade-karim", name="Kevin Vance (Tile Installer)", phone="+1-555-018-2233", trade="Master Tiler", city="Metro Area", rating=4.4, reliability_score=83),
            Tradesperson(id="trade-mustapha", name="David Chen (Finish Painter)", phone="+1-555-018-3344", trade="Finish Painter", city="Metro Area", rating=4.8, reliability_score=93),
            Tradesperson(id="trade-ali", name="James Wilson (Licensed Plumber)", phone="+1-555-018-4455", trade="Licensed Plumber", city="Metro Area", rating=4.7, reliability_score=90),
            Tradesperson(id="trade-sofiane", name="Anthony Brooks (Master Electrician)", phone="+1-555-018-5566", trade="Master Electrician", city="Metro Area", rating=4.8, reliability_score=91),
        ]

        # Reference Showcase Project
        p_id = "proj-apt-f4"
        room_salon = Room(
            id="room-salon",
            name="Open Living & Dining Room",
            length=25.0,
            width=16.0,
            height=9.0,
            surface=400.0,
            renovation_types=["Wall & ceiling paint", "Recessed LED ceiling", "Hardwood flooring prep"],
            notes="South-facing natural light, dimmable LED zones required.",
        )
        room_cuisine = Room(
            id="room-cuisine",
            name="Chef's Kitchen",
            length=15.0,
            width=12.0,
            height=9.0,
            surface=180.0,
            renovation_types=["Porcelain floor tile", "Backsplash installation", "Plumbing rough-in & sink"],
            notes="Requires new dual undermount sink connections and island wiring.",
        )
        room_sdb = Room(
            id="room-sdb",
            name="Master Bathroom Suite",
            length=12.0,
            width=8.0,
            height=8.5,
            surface=96.0,
            renovation_types=["Wall & floor tile", "Walk-in shower pan", "Vanity faucets", "Sanitary plumbing"],
            notes="Full waterproof membrane waterproofing required for curbless shower.",
        )

        req_carrelage = Requirement(
            id="req-carrelage",
            room_id="room-sdb",
            room_name="Master Bath + Kitchen",
            category="Flooring",
            item_name="Porcelain Floor Tiles 24x24 (Calacatta Marble Finish)",
            quantity=520.0,
            unit="sq ft",
            item_type="material",
            estimated_unit_price=4.50,
            notes="High-traffic porcelain, rectified edges with 10% cut allowance.",
        )
        req_peinture = Requirement(
            id="req-peinture",
            room_id="room-salon",
            room_name="Open Living & Dining Room",
            category="Paint",
            item_name="Premium Interior Velvet Matte Paint (Ultra Durable)",
            quantity=10.0,
            unit="gal",
            item_type="material",
            estimated_unit_price=65.0,
            notes="Warm Alabaster tone, zero-VOC formula.",
        )
        req_led = Requirement(
            id="req-led",
            room_id="room-salon",
            room_name="Open Living & Dining Room",
            category="Electrical",
            item_name="7W Dimmable Recessed LED Downlights (3000K Warm White)",
            quantity=24.0,
            unit="units",
            item_type="material",
            estimated_unit_price=22.0,
            notes="IC-rated, airtight housing included.",
        )
        req_robinet = Requirement(
            id="req-robinet",
            room_id="room-sdb",
            room_name="Master Bath & Kitchen",
            category="Plumbing",
            item_name="Designer Brushed Brass Thermostatic Mixer Faucets",
            quantity=3.0,
            unit="units",
            item_type="material",
            estimated_unit_price=185.0,
            notes="Solid brass body, ceramic disc cartridges.",
        )

        # Subcontractor Labor Requirements
        req_labor_carreleur = Requirement(
            id="req-labor-carreleur",
            room_id="room-sdb",
            room_name="Jobsite Wide",
            category="Labor",
            item_name="Tile & Substrate Installation (Master Tiler)",
            quantity=4.0,
            unit="days",
            item_type="labor",
            estimated_unit_price=450.0,
            notes="520 sq ft porcelain layout + precision miter cuts.",
        )
        req_labor_peintre = Requirement(
            id="req-labor-peintre",
            room_id="room-salon",
            room_name="Jobsite Wide",
            category="Labor",
            item_name="Surface Prep & 2-Coat Painting (Finish Painter)",
            quantity=3.0,
            unit="days",
            item_type="labor",
            estimated_unit_price=380.0,
            notes="Level 4 drywall finish, masking, primer + 2 topcoats.",
        )
        req_labor_plombier = Requirement(
            id="req-labor-plombier",
            room_id="room-sdb",
            room_name="Master Bath & Kitchen",
            category="Labor",
            item_name="Sanitary Rough-in & Trim Installation (Licensed Plumber)",
            quantity=2.0,
            unit="days",
            item_type="labor",
            estimated_unit_price=520.0,
            notes="Shower valves, vanity lines, and kitchen sink rough-ins.",
        )
        req_labor_elec = Requirement(
            id="req-labor-elec",
            room_id="room-salon",
            room_name="Open Living Room",
            category="Labor",
            item_name="Recessed Lighting Circuitry & Smart Dimmer Trim (Master Electrician)",
            quantity=2.0,
            unit="days",
            item_type="labor",
            estimated_unit_price=500.0,
            notes="NEC compliance, 3 dedicated circuits with smart control switches.",
        )

        # Initial Vendor & Trade Offers
        offer_b = Offer(
            id="off-ceram-b",
            project_id=p_id,
            requirement_id="req-carrelage",
            requirement_name="Porcelain Floor Tiles 24x24 (Calacatta Marble Finish)",
            target_type="supplier",
            target_id="sup-ceram-b",
            target_name="Apex Tile & Stone Direct (Supplier B)",
            target_phone="+1-555-019-2831",
            unit_price=4.25,
            quantity_available=650.0,
            discount_percent=5.0,
            delivery_days=3,
            delivery_available=True,
            delivery_cost=0.0,
            reliability_score=92,
            calculated_score=91.5,
            is_recommended=True,
            is_selected=True,
            notes="Balanced offer with 5% negotiated volume discount, in stock.",
        )

        offer_a = Offer(
            id="off-ceram-a",
            project_id=p_id,
            requirement_id="req-carrelage",
            requirement_name="Porcelain Floor Tiles 24x24 (Calacatta Marble Finish)",
            target_type="supplier",
            target_id="sup-ceram-a",
            target_name="Grand Surface Materials (Supplier A)",
            target_phone="+1-555-019-3344",
            unit_price=4.80,
            quantity_available=550.0,
            discount_percent=0.0,
            delivery_days=1,
            delivery_available=True,
            delivery_cost=45.0,
            reliability_score=85,
            calculated_score=81.0,
            is_recommended=False,
            is_selected=False,
            notes="Next-day delivery available but unit price is higher.",
        )

        offer_c = Offer(
            id="off-ceram-c",
            project_id=p_id,
            requirement_id="req-carrelage",
            requirement_name="Porcelain Floor Tiles 24x24 (Calacatta Marble Finish)",
            target_type="supplier",
            target_id="sup-ceram-c",
            target_name="Atlas Porcelain Warehouse (Supplier C)",
            target_phone="+1-555-019-4455",
            unit_price=3.95,
            quantity_available=400.0,
            discount_percent=0.0,
            delivery_days=10,
            delivery_available=False,
            delivery_cost=0.0,
            reliability_score=78,
            calculated_score=72.0,
            is_recommended=False,
            is_selected=False,
            notes="Lowest price, but 10-day lead time and customer pickup only.",
        )

        offer_peinture = Offer(
            id="off-peint-a",
            project_id=p_id,
            requirement_id="req-peinture",
            requirement_name="Premium Interior Velvet Matte Paint (Ultra Durable)",
            target_type="supplier",
            target_id="sup-peint-a",
            target_name="Sherwin ProFinish Coatings",
            target_phone="+1-555-019-5566",
            unit_price=60.0,
            quantity_available=50.0,
            discount_percent=5.0,
            delivery_days=1,
            delivery_available=True,
            delivery_cost=0.0,
            reliability_score=95,
            calculated_score=94.0,
            is_recommended=True,
            is_selected=True,
            notes="Commercial contractor discount applied, immediate availability.",
        )

        offer_led = Offer(
            id="off-elec-a",
            project_id=p_id,
            requirement_id="req-led",
            requirement_name="7W Dimmable Recessed LED Downlights (3000K Warm White)",
            target_type="supplier",
            target_id="sup-elec-a",
            target_name="Metro Lighting & Electric Supply",
            target_phone="+1-555-019-7788",
            unit_price=19.50,
            quantity_available=100.0,
            discount_percent=5.0,
            delivery_days=1,
            delivery_available=True,
            delivery_cost=0.0,
            reliability_score=90,
            calculated_score=91.5,
            is_recommended=True,
            is_selected=True,
            notes="Bulk pack pricing with free jobsite direct drop.",
        )

        offer_robinet = Offer(
            id="off-plomb-a",
            project_id=p_id,
            requirement_id="req-robinet",
            requirement_name="Designer Brushed Brass Thermostatic Mixer Faucets",
            target_type="supplier",
            target_id="sup-plomb-a",
            target_name="Prestige Bath & Plumbing Fixtures",
            target_phone="+1-555-019-8899",
            unit_price=175.0,
            quantity_available=12.0,
            discount_percent=0.0,
            delivery_days=2,
            delivery_available=True,
            delivery_cost=0.0,
            reliability_score=88,
            calculated_score=89.0,
            is_recommended=True,
            is_selected=True,
            notes="5-year commercial manufacturer warranty included.",
        )

        # Subcontractor Offers
        offer_artisan_mohamed = Offer(
            id="off-trade-mohamed",
            project_id=p_id,
            requirement_id="req-labor-carreleur",
            requirement_name="Tile & Substrate Installation (Master Tiler)",
            target_type="tradesperson",
            target_id="trade-mohamed",
            target_name="Marcus Reed (Master Tiler)",
            target_phone="+1-555-018-1122",
            unit_price=425.0,
            quantity_available=4.0,
            discount_percent=0.0,
            delivery_days=2,
            delivery_available=True,
            delivery_cost=0.0,
            reliability_score=95,
            calculated_score=94.5,
            is_recommended=True,
            is_selected=True,
            notes="Earliest start date: 3 business days, laser leveling equipment.",
        )

        offer_artisan_peintre = Offer(
            id="off-trade-mustapha",
            project_id=p_id,
            requirement_id="req-labor-peintre",
            requirement_name="Surface Prep & 2-Coat Painting (Finish Painter)",
            target_type="tradesperson",
            target_id="trade-mustapha",
            target_name="David Chen (Finish Painter)",
            target_phone="+1-555-018-3344",
            unit_price=360.0,
            quantity_available=3.0,
            discount_percent=0.0,
            delivery_days=3,
            delivery_available=True,
            delivery_cost=0.0,
            reliability_score=93,
            calculated_score=92.5,
            is_recommended=True,
            is_selected=True,
            notes="HEPA air scrubbers and floor protection tarps provided.",
        )

        offer_artisan_plombier = Offer(
            id="off-trade-ali",
            project_id=p_id,
            requirement_id="req-labor-plombier",
            requirement_name="Sanitary Rough-in & Trim Installation (Licensed Plumber)",
            target_type="tradesperson",
            target_id="trade-ali",
            target_name="James Wilson (Licensed Plumber)",
            target_phone="+1-555-018-4455",
            unit_price=490.0,
            quantity_available=2.0,
            discount_percent=0.0,
            delivery_days=2,
            delivery_available=True,
            delivery_cost=0.0,
            reliability_score=90,
            calculated_score=91.0,
            is_recommended=True,
            is_selected=True,
            notes="Master licensed, specialized in PEX expansion and brass trims.",
        )

        offer_artisan_elec = Offer(
            id="off-trade-sofiane",
            project_id=p_id,
            requirement_id="req-labor-elec",
            requirement_name="Recessed Lighting Circuitry & Smart Dimmer Trim (Master Electrician)",
            target_type="tradesperson",
            target_id="trade-sofiane",
            target_name="Anthony Brooks (Master Electrician)",
            target_phone="+1-555-018-5566",
            unit_price=480.0,
            quantity_available=2.0,
            discount_percent=0.0,
            delivery_days=2,
            delivery_available=True,
            delivery_cost=0.0,
            reliability_score=91,
            calculated_score=91.0,
            is_recommended=True,
            is_selected=True,
            notes="Full municipal permit sign-off capable.",
        )

        # Archived CALL-E Autonomous Call
        sample_call = CallRecord(
            id="call-rec-ceram-b",
            project_id=p_id,
            target_type="supplier",
            target_id="sup-ceram-b",
            target_name="Apex Tile & Stone Direct (Supplier B)",
            target_phone="+1-555-019-2831",
            requirement_id="req-carrelage",
            requirement_name="Porcelain Floor Tiles 24x24",
            status="completed",
            duration_seconds=42,
            calle_call_id="calle_live_09b8f21a",
            transcript=[
                {"speaker": "AI", "text": "Hi, I'm calling from ContractorPilot on behalf of a residential remodel jobsite. Do you have 520 sq ft of 24x24 Calacatta porcelain floor tiles in stock?"},
                {"speaker": "Contact", "text": "Hello! Yes, we have 650 sq ft available right now in our regional warehouse."},
                {"speaker": "AI", "text": "Great. What is your wholesale contractor price per sq ft, and can you deliver to the jobsite?"},
                {"speaker": "Contact", "text": "List is $4.50 per sq ft. For an order of 520 sq ft, we can apply a 5% trade discount down to $4.25. Free direct freight delivery in 3 business days."},
                {"speaker": "AI", "text": "Confirmed: $4.25 per sq ft with a 5% discount, 650 sq ft in stock, delivery in 3 days. Thank you for the quick quote!"},
                {"speaker": "Contact", "text": "You're welcome! Let us know whenever you're ready to place the PO."}
            ],
            extracted_data={
                "supplier": "Apex Tile & Stone Direct (Supplier B)",
                "product": "Porcelain Floor Tiles 24x24",
                "quantity_requested": 520.0,
                "unit": "sq ft",
                "unit_price": 4.25,
                "discount_percent": 5.0,
                "availability": 650.0,
                "delivery_days": 3,
                "delivery_available": True
            }
        )

        sample_project = Project(
            id=p_id,
            name="Modern Luxury Condo Remodel — 1,300 sq ft",
            client_name="The Miller Residence",
            client_phone="+1-555-321-7890",
            client_email="miller.remodel@example.com",
            location="742 Evergreen Terrace, Metro District",
            surface_sqm=120.8,
            project_type="Complete Residential Interior Remodel",
            status="COMPARISON",
            rooms=[room_salon, room_cuisine, room_sdb],
            requirements=[
                req_carrelage, req_peinture, req_led, req_robinet,
                req_labor_carreleur, req_labor_peintre, req_labor_plombier, req_labor_elec
            ],
            offers=[
                offer_b, offer_a, offer_c,
                offer_peinture, offer_led, offer_robinet,
                offer_artisan_mohamed, offer_artisan_peintre, offer_artisan_plombier, offer_artisan_elec
            ],
            call_records=[sample_call],
        )

        self.projects[p_id] = sample_project


# Singleton instance
store = DataStore()
