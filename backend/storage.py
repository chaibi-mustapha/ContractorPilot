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
    length: float  # mètres
    width: float   # mètres
    height: float = 2.70 # mètres
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
    category: str  # Peinture, Sol, Électricité, Plomberie, Sanitaire, Menuiserie, Main-d'œuvre
    item_name: str
    quantity: float
    unit: str  # m², L, unité, jour, ensemble
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
    reliability_score: int = 90  # sur 100


class Tradesperson(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    phone: str
    trade: str  # Carreleur, Peintre, Plombier, Électricien, Menuisier
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
    quote_number: str = "REN-2026-001"
    date_str: str = Field(default_factory=lambda: datetime.now().strftime("%d/%m/%Y"))
    materials_subtotal: float = 0.0
    labor_subtotal: float = 0.0
    base_cost_total: float = 0.0
    margin_percent: float = 20.0
    margin_amount: float = 0.0
    expenses_amount: float = 0.0  # Frais de transport/gestion
    tax_percent: float = 0.0
    tax_amount: float = 0.0
    grand_total: float = 0.0
    currency: str = "DA"
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
    project_type: str = "Rénovation d'intérieur"
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
        # Default Suppliers
        self.suppliers = [
            Supplier(id="sup-ceram-b", name="Comptoir Céramique Moderne (Fournisseur B)", phone="+213550112233", category="Sol & Carrelage", city="Alger", rating=4.8, reliability_score=92),
            Supplier(id="sup-ceram-a", name="Grand Décor Carrelage (Fournisseur A)", phone="+213551223344", category="Sol & Carrelage", city="Alger", rating=4.5, reliability_score=85),
            Supplier(id="sup-ceram-c", name="Atlas Sanitaire & Faïence (Fournisseur C)", phone="+213552334455", category="Sol & Carrelage", city="Blida", rating=4.2, reliability_score=78),
            Supplier(id="sup-peint-a", name="Peintures & Nuances Pro", phone="+213553445566", category="Peinture & Revêtements", city="Alger", rating=4.9, reliability_score=95),
            Supplier(id="sup-peint-b", name="Coloris Express Matériaux", phone="+213554556677", category="Peinture & Revêtements", city="Alger", rating=4.3, reliability_score=82),
            Supplier(id="sup-elec-a", name="Luminaire & Élec Distribution", phone="+213555667788", category="Électricité & Éclairage", city="Alger", rating=4.7, reliability_score=90),
            Supplier(id="sup-plomb-a", name="Robinetterie & Bain Prestige", phone="+213556778899", category="Plomberie & Sanitaire", city="Alger", rating=4.6, reliability_score=88),
        ]

        # Default Tradespeople
        self.tradespeople = [
            Tradesperson(id="trade-mohamed", name="Artisan Mohamed (Carreleur)", phone="+213661112233", trade="Carreleur", city="Alger", rating=4.9, reliability_score=95),
            Tradesperson(id="trade-karim", name="Artisan Karim (Carreleur)", phone="+213662223344", trade="Carreleur", city="Alger", rating=4.4, reliability_score=83),
            Tradesperson(id="trade-mustapha", name="Artisan Mustapha (Peintre)", phone="+213663334455", trade="Peintre", city="Alger", rating=4.8, reliability_score=93),
            Tradesperson(id="trade-ali", name="Artisan Ali (Plombier)", phone="+213664445566", trade="Plombier", city="Alger", rating=4.7, reliability_score=90),
            Tradesperson(id="trade-sofiane", name="Artisan Sofiane (Électricien)", phone="+213665556677", trade="Électricien", city="Alger", rating=4.8, reliability_score=91),
        ]

        # Reference Demo Project (from RENOVAI_CALL_E_PROJET_COMPLET.md)
        p_id = "proj-apt-f4"
        room_salon = Room(
            id="room-salon",
            name="Grand Salon & Séjour",
            length=7.5,
            width=5.0,
            height=2.8,
            surface=37.5,
            renovation_types=["Peinture murs & plafonds", "Faux plafond LED", "Nouveau sol parquet"],
            notes="Exposition sud, besoin d'éclairage spot LED intégré.",
        )
        room_cuisine = Room(
            id="room-cuisine",
            name="Cuisine Ouverte",
            length=4.5,
            width=3.5,
            height=2.8,
            surface=15.75,
            renovation_types=["Carrelage sol", "Crédence", "Évier et robinetterie"],
            notes="Arrivées d'eau à rénover, évier inox double bac.",
        )
        room_sdb = Room(
            id="room-sdb",
            name="Salle de bain principale",
            length=3.2,
            width=2.4,
            height=2.7,
            surface=7.68,
            renovation_types=["Carrelage sol & mural", "Douche italienne", "Lavabo et robinetterie", "Plomberie"],
            notes="Étanchéité complète nécessaire pour la douche à l'italienne.",
        )

        req_carrelage = Requirement(
            id="req-carrelage",
            room_id="room-sdb",
            room_name="Salle de bain + Cuisine",
            category="Sol",
            item_name="Carrelage modèle X (Grès Cérame 60x60)",
            quantity=48.0,
            unit="m²",
            item_type="material",
            estimated_unit_price=2600.0,
            notes="Besoin urgent pour la salle de bain et cuisine.",
        )
        req_peinture = Requirement(
            id="req-peinture",
            room_id="room-salon",
            room_name="Grand Salon & Séjour",
            category="Peinture",
            item_name="Peinture murale satinée lavable haute qualité",
            quantity=35.0,
            unit="L",
            item_type="material",
            estimated_unit_price=1200.0,
            notes="Teinte blanc cassé velours.",
        )
        req_led = Requirement(
            id="req-led",
            room_id="room-salon",
            room_name="Grand Salon & Séjour",
            category="Électricité",
            item_name="Spots encastrés LED 7W Dimmables",
            quantity=24.0,
            unit="unités",
            item_type="material",
            estimated_unit_price=1200.0,
            notes="Blanc chaud 3000K.",
        )
        req_robinet = Requirement(
            id="req-robinet",
            room_id="room-sdb",
            room_name="Salle de bain & Cuisine",
            category="Plomberie",
            item_name="Mitigeur thermostatique de qualité",
            quantity=3.0,
            unit="unités",
            item_type="material",
            estimated_unit_price=10500.0,
            notes="Finition chromée ou noir mat.",
        )

        # Main-d'œuvre
        req_labor_carreleur = Requirement(
            id="req-labor-carreleur",
            room_id="room-sdb",
            room_name="Chantier complet",
            category="Main-d'œuvre",
            item_name="Pose Carrelage & Faïence (Carreleur qualifié)",
            quantity=4.0,
            unit="jours",
            item_type="labor",
            estimated_unit_price=14500.0,
            notes="48 m² de pose + découpes d'angles.",
        )
        req_labor_peintre = Requirement(
            id="req-labor-peintre",
            room_id="room-salon",
            room_name="Chantier complet",
            category="Main-d'œuvre",
            item_name="Travaux de peinture & enduit (Peintre en bâtiment)",
            quantity=3.0,
            unit="jours",
            item_type="labor",
            estimated_unit_price=15000.0,
            notes="Préparation des murs, 2 couches d'enduit + 2 couches de peinture.",
        )
        req_labor_plombier = Requirement(
            id="req-labor-plombier",
            room_id="room-sdb",
            room_name="Salle de bain & Cuisine",
            category="Main-d'œuvre",
            item_name="Installation plomberie sanitaire (Plombier)",
            quantity=2.0,
            unit="jours",
            item_type="labor",
            estimated_unit_price=16000.0,
            notes="Raccordements douche, lavabos et évier.",
        )
        req_labor_elec = Requirement(
            id="req-labor-elec",
            room_id="room-salon",
            room_name="Grand Salon",
            category="Main-d'œuvre",
            item_name="Câblage faux plafond & pose spots (Électricien)",
            quantity=2.0,
            unit="jours",
            item_type="labor",
            estimated_unit_price=17500.0,
            notes="Circuits séparés avec variateur.",
        )

        # Offres initiales représentatives (du scénario documenté)
        offer_b = Offer(
            id="off-ceram-b",
            project_id=p_id,
            requirement_id="req-carrelage",
            requirement_name="Carrelage modèle X (Grès Cérame 60x60)",
            target_type="supplier",
            target_id="sup-ceram-b",
            target_name="Comptoir Céramique Moderne (Fournisseur B)",
            target_phone="+213550112233",
            unit_price=2650.0,
            quantity_available=60.0,
            discount_percent=5.0,
            delivery_days=3,
            delivery_available=True,
            delivery_cost=0.0,
            reliability_score=92,
            calculated_score=88.5,
            is_recommended=True,
            is_selected=True,
            notes="Offre équilibrée avec 5% de remise et 60 m² dispo.",
        )

        offer_a = Offer(
            id="off-ceram-a",
            project_id=p_id,
            requirement_id="req-carrelage",
            requirement_name="Carrelage modèle X (Grès Cérame 60x60)",
            target_type="supplier",
            target_id="sup-ceram-a",
            target_name="Grand Décor Carrelage (Fournisseur A)",
            target_phone="+213551223344",
            unit_price=2850.0,
            quantity_available=80.0,
            discount_percent=0.0,
            delivery_days=1,
            delivery_available=True,
            delivery_cost=2500.0,
            reliability_score=85,
            calculated_score=82.0,
            is_recommended=False,
            is_selected=False,
            notes="Livraison sous 24h mais prix plus élevé.",
        )

        offer_c = Offer(
            id="off-ceram-c",
            project_id=p_id,
            requirement_id="req-carrelage",
            requirement_name="Carrelage modèle X (Grès Cérame 60x60)",
            target_type="supplier",
            target_id="sup-ceram-c",
            target_name="Atlas Sanitaire & Faïence (Fournisseur C)",
            target_phone="+213552334455",
            unit_price=2490.0,
            quantity_available=48.0,
            discount_percent=0.0,
            delivery_days=10,
            delivery_available=False,
            delivery_cost=0.0,
            reliability_score=78,
            calculated_score=75.5,
            is_recommended=False,
            is_selected=False,
            notes="Prix le plus bas mais délai de 10 jours et pas de livraison.",
        )

        # Offre Peinture
        offer_peinture = Offer(
            id="off-peint-a",
            project_id=p_id,
            requirement_id="req-peinture",
            requirement_name="Peinture murale satinée lavable haute qualité",
            target_type="supplier",
            target_id="sup-peint-a",
            target_name="Peintures & Nuances Pro",
            target_phone="+213553445566",
            unit_price=1200.0,
            quantity_available=50.0,
            discount_percent=0.0,
            delivery_days=1,
            delivery_available=True,
            delivery_cost=0.0,
            reliability_score=95,
            calculated_score=93.0,
            is_recommended=True,
            is_selected=True,
            notes="Qualité premium professionnelle, stock immédiat.",
        )

        # Offre Spots LED
        offer_led = Offer(
            id="off-elec-a",
            project_id=p_id,
            requirement_id="req-led",
            requirement_name="Spots encastrés LED 7W Dimmables",
            target_type="supplier",
            target_id="sup-elec-a",
            target_name="Luminaire & Élec Distribution",
            target_phone="+213555667788",
            unit_price=1200.0,
            quantity_available=100.0,
            discount_percent=0.0,
            delivery_days=1,
            delivery_available=True,
            delivery_cost=0.0,
            reliability_score=90,
            calculated_score=91.0,
            is_recommended=True,
            is_selected=True,
            notes="Livraison groupée offerte.",
        )

        # Offre Robinetterie
        offer_robinet = Offer(
            id="off-plomb-a",
            project_id=p_id,
            requirement_id="req-robinet",
            requirement_name="Mitigeur thermostatique de qualité",
            target_type="supplier",
            target_id="sup-plomb-a",
            target_name="Robinetterie & Bain Prestige",
            target_phone="+213556778899",
            unit_price=10500.0,
            quantity_available=10.0,
            discount_percent=0.0,
            delivery_days=2,
            delivery_available=True,
            delivery_cost=0.0,
            reliability_score=88,
            calculated_score=89.0,
            is_recommended=True,
            is_selected=True,
            notes="Garantie 5 ans constructeur.",
        )

        # Offres Artisans
        offer_artisan_mohamed = Offer(
            id="off-trade-mohamed",
            project_id=p_id,
            requirement_id="req-labor-carreleur",
            requirement_name="Pose Carrelage & Faïence (Carreleur qualifié)",
            target_type="tradesperson",
            target_id="trade-mohamed",
            target_name="Artisan Mohamed (Carreleur)",
            target_phone="+213661112233",
            unit_price=14500.0,
            quantity_available=4.0,
            discount_percent=0.0,
            delivery_days=2,
            delivery_available=True,
            delivery_cost=0.0,
            reliability_score=95,
            calculated_score=94.0,
            is_recommended=True,
            is_selected=True,
            notes="Disponibilité confirmée dès le 3 du mois.",
        )

        offer_artisan_peintre = Offer(
            id="off-trade-mustapha",
            project_id=p_id,
            requirement_id="req-labor-peintre",
            requirement_name="Travaux de peinture & enduit (Peintre en bâtiment)",
            target_type="tradesperson",
            target_id="trade-mustapha",
            target_name="Artisan Mustapha (Peintre)",
            target_phone="+213663334455",
            unit_price=15000.0,
            quantity_available=3.0,
            discount_percent=0.0,
            delivery_days=3,
            delivery_available=True,
            delivery_cost=0.0,
            reliability_score=93,
            calculated_score=92.5,
            is_recommended=True,
            is_selected=True,
            notes="Équipement complet d'aspiration poussière et protection bâches.",
        )

        offer_artisan_plombier = Offer(
            id="off-trade-ali",
            project_id=p_id,
            requirement_id="req-labor-plombier",
            requirement_name="Installation plomberie sanitaire (Plombier)",
            target_type="tradesperson",
            target_id="trade-ali",
            target_name="Artisan Ali (Plombier)",
            target_phone="+213664445566",
            unit_price=16000.0,
            quantity_available=2.0,
            discount_percent=0.0,
            delivery_days=2,
            delivery_available=True,
            delivery_cost=0.0,
            reliability_score=90,
            calculated_score=90.0,
            is_recommended=True,
            is_selected=True,
            notes="Spécialiste douche à l'italienne et sertissage multicouche.",
        )

        offer_artisan_elec = Offer(
            id="off-trade-sofiane",
            project_id=p_id,
            requirement_id="req-labor-elec",
            requirement_name="Câblage faux plafond & pose spots (Électricien)",
            target_type="tradesperson",
            target_id="trade-sofiane",
            target_name="Artisan Sofiane (Électricien)",
            target_phone="+213665556677",
            unit_price=17500.0,
            quantity_available=2.0,
            discount_percent=0.0,
            delivery_days=2,
            delivery_available=True,
            delivery_cost=0.0,
            reliability_score=91,
            calculated_score=91.0,
            is_recommended=True,
            is_selected=True,
            notes="Norme NFC 15-100 respectée.",
        )

        # Exemple d'appel CALL-E déjà archivé dans le dossier projet
        sample_call = CallRecord(
            id="call-rec-ceram-b",
            project_id=p_id,
            target_type="supplier",
            target_id="sup-ceram-b",
            target_name="Comptoir Céramique Moderne (Fournisseur B)",
            target_phone="+213550112233",
            requirement_id="req-carrelage",
            requirement_name="Carrelage modèle X",
            status="completed",
            duration_seconds=42,
            calle_call_id="calle_live_09b8f21a",
            transcript=[
                {"speaker": "AI", "text": "Bonjour, je vous appelle au nom de l'entreprise ContractorPilot pour une demande de prix de chantier. Avez-vous 48 m² de carrelage modèle X disponibles ?"},
                {"speaker": "Contact", "text": "Bonjour ! Oui tout à fait, nous avons actuellement 60 mètres carrés en stock au dépôt."},
                {"speaker": "AI", "text": "Parfait. Quel est votre tarif unitaire au mètre carré et pouvez-vous livrer sur le chantier ?"},
                {"speaker": "Contact", "text": "Le prix catalogue est de 2 650 DA le m². Pour 48 m² nous pouvons vous accorder 5 % de remise commerciale, et la livraison est assurée sous 3 jours ouvrés."},
                {"speaker": "AI", "text": "C'est bien noté : 2 650 DA le m², remise 5%, 60 m² dispo, livraison 3 jours. Merci beaucoup et bonne journée !"},
                {"speaker": "Contact", "text": "Je vous en prie, à votre disposition pour le bon de commande. Bonne journée."}
            ],
            extracted_data={
                "supplier": "Comptoir Céramique Moderne (Fournisseur B)",
                "product": "Carrelage modèle X",
                "quantity_requested": 48.0,
                "unit": "m²",
                "unit_price": 2650.0,
                "discount_percent": 5.0,
                "availability": 60.0,
                "delivery_days": 3,
                "delivery_available": True
            }
        )

        sample_project = Project(
            id=p_id,
            name="Rénovation Appartement F4 — 120 m²",
            client_name="Famille Benali",
            client_phone="+213555998877",
            client_email="benali.renov@example.com",
            location="Sidi Yahia, Hydra, Alger",
            surface_sqm=120.0,
            project_type="Rénovation complète d'intérieur",
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
