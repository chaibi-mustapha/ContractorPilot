import asyncio
import os
import random
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

try:
    import calle
    HAS_CALLE_SDK = True
except ImportError:
    HAS_CALLE_SDK = False

CALLE_API_KEY = os.getenv("CALLE_API_KEY", "")


class CalleService:
    def __init__(self) -> None:
        self.api_key = os.getenv("CALLE_API_KEY", "")
        self.client: Optional[Any] = None
        if HAS_CALLE_SDK and self.api_key:
            try:
                self.client = calle.CalleClient(api_key=self.api_key)
            except Exception as e:
                print(f"[CALL-E] Warning: Could not initialize CalleClient: {e}")

    def update_api_key(self, api_key: str) -> None:
        self.api_key = api_key
        os.environ["CALLE_API_KEY"] = api_key
        if HAS_CALLE_SDK and api_key:
            self.client = calle.CalleClient(api_key=api_key)
        else:
            self.client = None

    def is_live_ready(self) -> bool:
        return bool(HAS_CALLE_SDK and self.client and self.api_key)

    def build_call_task(
        self,
        target_type: str,
        target_name: str,
        target_phone: str,
        requirement_name: str,
        quantity: float,
        unit: str,
        project_location: str = "Alger"
    ) -> str:
        """Génère la consigne vocale pour l'agent CALL-E."""
        if target_type == "supplier":
            return (
                f"You are ContractorPilot's procurement agent calling supplier '{target_name}' at {target_phone}. "
                f"Your goal is to source '{requirement_name}' for a renovation project in {project_location}. "
                f"Specifically ask: "
                f"1) Do they have at least {quantity} {unit} in stock? "
                f"2) What is their unit price per {unit}? "
                f"3) Can they deliver to {project_location}, and what are the delivery time and cost? "
                f"4) Is there any volume discount for an order of {quantity} {unit}? "
                f"Be polite, professional, concise, and confirm all numbers clearly."
            )
        else:
            return (
                f"You are ContractorPilot's project manager calling tradesperson '{target_name}' at {target_phone}. "
                f"Your goal is to inquire about availability and pricing for: '{requirement_name}' ({quantity} {unit}) "
                f"on a renovation site located in {project_location}. "
                f"Specifically ask: "
                f"1) Their availability and earliest start date? "
                f"2) Their rate per {unit} or daily rate? "
                f"3) Estimated duration to complete the work? "
                f"4) If they bring their own equipment or require specific site preparations. "
                f"Be professional, clear, and note down all specific terms."
            )

    def get_result_schema(self, target_type: str) -> Dict[str, Any]:
        """Définit le schéma JSON de résultat pour CALL-E."""
        if target_type == "supplier":
            return {
                "type": "object",
                "properties": {
                    "supplier_name": {"type": "string"},
                    "product_name": {"type": "string"},
                    "unit_price": {"type": "number", "description": "Prix unitaire HT/TTC en monnaie locale"},
                    "quantity_available": {"type": "number", "description": "Quantité actuellement disponible en stock"},
                    "discount_percent": {"type": "number", "description": "Pourcentage de remise accordé (ex: 5 pour 5%)"},
                    "delivery_available": {"type": "boolean", "description": "Si la livraison sur chantier est possible"},
                    "delivery_days": {"type": "integer", "description": "Délai de livraison estimé en jours ouvrés"},
                    "delivery_cost": {"type": "number", "description": "Coût de la livraison en monnaie locale"},
                    "terms_notes": {"type": "string", "description": "Observations ou conditions particulières"}
                },
                "required": ["unit_price", "quantity_available", "delivery_days"]
            }
        else:
            return {
                "type": "object",
                "properties": {
                    "tradesperson_name": {"type": "string"},
                    "trade": {"type": "string"},
                    "unit_price": {"type": "number", "description": "Tarif journalier ou prix unitaire de la prestation"},
                    "is_available": {"type": "boolean", "description": "Disponibilité pour le chantier"},
                    "available_date": {"type": "string", "description": "Date de début possible"},
                    "estimated_duration_days": {"type": "integer", "description": "Durée estimée des travaux"},
                    "terms_notes": {"type": "string", "description": "Conditions ou matériel inclus"}
                },
                "required": ["unit_price", "is_available", "estimated_duration_days"]
            }

    async def execute_live_call(
        self,
        target_type: str,
        target_name: str,
        target_phone: str,
        requirement_name: str,
        quantity: float,
        unit: str,
        project_location: str = "Alger"
    ) -> Dict[str, Any]:
        """Exécute un appel réel via l'API CALL-E."""
        if not self.is_live_ready():
            raise ValueError("CALL-E SDK is not configured with a valid CALLE_API_KEY.")

        task = self.build_call_task(
            target_type=target_type,
            target_name=target_name,
            target_phone=target_phone,
            requirement_name=requirement_name,
            quantity=quantity,
            unit=unit,
            project_location=project_location
        )
        schema = self.get_result_schema(target_type)

        loop = asyncio.get_event_loop()
        # Call in executor to avoid blocking the event loop
        response = await loop.run_in_executor(
            None,
            lambda: self.client.calls.create_and_wait(
                task=task,
                recipient={"phone": target_phone, "name": target_name},
                result_schema=schema,
                metadata={
                    "app": "ContractorPilot",
                    "requirement": requirement_name,
                    "target_type": target_type
                }
            )
        )
        return response

    async def simulate_call_stream(
        self,
        target_type: str,
        target_name: str,
        target_phone: str,
        requirement_name: str,
        quantity: float,
        unit: str,
        project_location: str = "Alger"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Simule un appel CALL-E interactif pas-à-pas en temps réel
        pour le streaming WebSocket sur le dashboard.
        """
        call_id = f"sim_{uuid.uuid4().hex[:8]}"
        
        # 1. Numérotation
        yield {
            "type": "status_update",
            "call_id": call_id,
            "status": "DIALING",
            "message": f"Numérotation de {target_name} ({target_phone})...",
            "timestamp": time.time()
        }
        await asyncio.sleep(1.2)

        # 2. Sonnerie
        yield {
            "type": "status_update",
            "call_id": call_id,
            "status": "RINGING",
            "message": "En attente de décrochage...",
            "timestamp": time.time()
        }
        await asyncio.sleep(1.5)

        # 3. Connecté
        yield {
            "type": "status_update",
            "call_id": call_id,
            "status": "CONNECTED",
            "message": "Appel décroché — Agent CALL-E en conversation vocale.",
            "timestamp": time.time()
        }
        await asyncio.sleep(0.8)

        # Scénario selon le type
        if target_type == "supplier":
            base_price = 2650.0 if "carrelage" in requirement_name.lower() else (
                1200.0 if "peinture" in requirement_name.lower() else (
                    1200.0 if "spot" in requirement_name.lower() or "led" in requirement_name.lower() else 10500.0
                )
            )
            # Variations légères selon le fournisseur
            if "Fournisseur A" in target_name:
                unit_price = round(base_price * 1.08, 0)
                stock = max(quantity + 20, 80.0)
                discount = 0.0
                lead_days = 1
                deliv_ok = True
                deliv_cost = 2500.0
            elif "Fournisseur C" in target_name:
                unit_price = round(base_price * 0.94, 0)
                stock = quantity
                discount = 0.0
                lead_days = 10
                deliv_ok = False
                deliv_cost = 0.0
            else: # Fournisseur B ou autre
                unit_price = base_price
                stock = max(quantity + 12, 60.0)
                discount = 5.0
                lead_days = 3
                deliv_ok = True
                deliv_cost = 0.0

            dialogue = [
                ("AI", f"Bonjour, je vous appelle au nom de l'entreprise de rénovation ContractorPilot. Nous avons un chantier à {project_location}. Avez-vous en stock {quantity} {unit} de {requirement_name} ?"),
                ("Contact", f"Bonjour ! Oui tout à fait, nous avons actuellement {int(stock)} {unit} disponibles immédiatement en dépôt."),
                ("AI", f"Très bien. Quel est votre tarif unitaire et assurez-vous la livraison sur le chantier ?"),
                ("Contact", f"Le prix unitaire est de {int(unit_price):,} DA.{' Pour ce volume de ' + str(quantity) + ' ' + unit + ', nous vous offrons 5% de remise commerciale.' if discount > 0 else ''} Livraison sous {lead_days} jours {'avec notre camion' if deliv_ok else 'ou à enlever directement en dépôt'}."),
                ("AI", f"Noté : {int(unit_price):,} DA par {unit}, remise {int(discount)}%, délai {lead_days} jours. Merci pour ces précisions rapides !"),
                ("Contact", "Avec plaisir, n'hésitez pas si vous avez besoin d'autres références.")
            ]

            extracted = {
                "supplier_name": target_name,
                "product_name": requirement_name,
                "unit_price": unit_price,
                "quantity_available": stock,
                "discount_percent": discount,
                "delivery_available": deliv_ok,
                "delivery_days": lead_days,
                "delivery_cost": deliv_cost,
                "terms_notes": "Offre collectée et normalisée par l'agent CALL-E."
            }

        else: # tradesperson
            daily_rate = 14500.0 if "carrel" in requirement_name.lower() else (
                15000.0 if "peint" in requirement_name.lower() else (
                    16000.0 if "plomb" in requirement_name.lower() else 17500.0
                )
            )
            est_days = int(quantity)

            dialogue = [
                ("AI", f"Bonjour maître artisan {target_name}, je vous contacte de la part de ContractorPilot pour un chantier à {project_location}. Seriez-vous disponible pour des travaux de {requirement_name} ({quantity} {unit}) ?"),
                ("Contact", f"Bonjour. Oui, j'ai une disponibilité possible dans la première semaine du mois. De quelle ampleur de travail s'agit-il ?"),
                ("AI", f"Il s'agit d'une intervention estimée à {quantity} {unit} sur un appartement. Quel serait votre tarif et votre délai d'intervention ?"),
                ("Contact", f"Pour cette prestation, mon tarif est de {int(daily_rate):,} DA par {unit}. Je peux démarrer sous 2 à 3 jours et finaliser le travail en {est_days} jours ouvrés avec mon matériel professionnel."),
                ("AI", f"C'est parfaitement clair : {int(daily_rate):,} DA par {unit}, démarrage rapide et fin en {est_days} jours. Merci beaucoup."),
                ("Contact", "Parfait, tenez-moi au courant dès que le chantier est prêt.")
            ]

            extracted = {
                "tradesperson_name": target_name,
                "trade": requirement_name,
                "unit_price": daily_rate,
                "is_available": True,
                "available_date": "Dès le 3 du mois",
                "estimated_duration_days": est_days,
                "terms_notes": "Artisan certifié, outillage complet et protections incluses."
            }

        # Stream dialogue turns
        for speaker, text in dialogue:
            yield {
                "type": "transcript_turn",
                "call_id": call_id,
                "speaker": speaker,
                "text": text,
                "timestamp": time.time()
            }
            # Realistic pause for speech flow
            await asyncio.sleep(1.2)

        # 4. Extraction structurée
        yield {
            "type": "extraction_ready",
            "call_id": call_id,
            "extracted_data": extracted,
            "timestamp": time.time()
        }
        await asyncio.sleep(0.5)

        # 5. Appel terminé
        yield {
            "type": "call_completed",
            "call_id": call_id,
            "status": "COMPLETED",
            "duration_seconds": random.randint(38, 55),
            "transcript": [{"speaker": s, "text": t} for s, t in dialogue],
            "extracted_data": extracted,
            "timestamp": time.time()
        }


# Global singleton instance
calle_service = CalleService()
