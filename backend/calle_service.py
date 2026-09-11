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
        project_location: str = "Metro Area"
    ) -> str:
        """Generates voice instructions for the CALL-E autonomous agent."""
        if target_type == "supplier":
            return (
                f"You are ContractorPilot's autonomous procurement agent calling supplier '{target_name}' at {target_phone}. "
                f"Your goal is to source '{requirement_name}' for an active residential remodel in {project_location}. "
                f"Specifically ask: "
                f"1) Do they have at least {quantity} {unit} in stock right now? "
                f"2) What is their wholesale contractor unit price per {unit}? "
                f"3) Can they deliver directly to {project_location}, and what are the delivery lead time and freight cost? "
                f"4) Can they apply any contractor or volume discount for an order of {quantity} {unit}? "
                f"Be polite, professional, concise, and confirm all numbers clearly."
            )
        else:
            return (
                f"You are ContractorPilot's project manager calling subcontractor '{target_name}' at {target_phone}. "
                f"Your goal is to inquire about availability and pricing for: '{requirement_name}' ({quantity} {unit}) "
                f"on a residential remodel located in {project_location}. "
                f"Specifically ask: "
                f"1) Their earliest availability and start date? "
                f"2) Their day rate or unit rate for this scope? "
                f"3) Estimated working days to complete the scope? "
                f"4) If they supply their own tools/equipment and dust mitigation tarps. "
                f"Be professional, clear, and confirm all agreed terms."
            )

    def get_result_schema(self, target_type: str) -> Dict[str, Any]:
        """Defines the structured JSON extraction schema for CALL-E."""
        if target_type == "supplier":
            return {
                "type": "object",
                "properties": {
                    "supplier_name": {"type": "string"},
                    "product_name": {"type": "string"},
                    "unit_price": {"type": "number", "description": "Unit price in USD ($)"},
                    "quantity_available": {"type": "number", "description": "Quantity currently available in warehouse stock"},
                    "discount_percent": {"type": "number", "description": "Percentage discount offered (e.g. 5 for 5%)"},
                    "delivery_available": {"type": "boolean", "description": "Whether jobsite delivery is available"},
                    "delivery_days": {"type": "integer", "description": "Estimated delivery lead time in business days"},
                    "delivery_cost": {"type": "number", "description": "Delivery freight fee in USD ($)"},
                    "terms_notes": {"type": "string", "description": "Warranty or special commercial terms"}
                },
                "required": ["unit_price", "quantity_available", "delivery_days"]
            }
        else:
            return {
                "type": "object",
                "properties": {
                    "tradesperson_name": {"type": "string"},
                    "trade": {"type": "string"},
                    "unit_price": {"type": "number", "description": "Daily labor rate in USD ($)"},
                    "is_available": {"type": "boolean", "description": "Availability for the remodel dates"},
                    "available_date": {"type": "string", "description": "Earliest confirmed start date"},
                    "estimated_duration_days": {"type": "integer", "description": "Estimated working days to complete scope"},
                    "terms_notes": {"type": "string", "description": "Licensing, tools, or site preparation requirements"}
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
        project_location: str = "Metro Area"
    ) -> Dict[str, Any]:
        """Executes a real phone call using the official CALL-E SDK."""
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
        project_location: str = "Metro Area"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Simulates an interactive step-by-step CALL-E phone call in real-time
        for live streaming over WebSocket to the dashboard.
        """
        call_id = f"sim_{uuid.uuid4().hex[:8]}"
        
        # 1. Dialing
        yield {
            "type": "status_update",
            "call_id": call_id,
            "status": "DIALING",
            "message": f"Dialing {target_name} ({target_phone})...",
            "timestamp": time.time()
        }
        await asyncio.sleep(1.2)

        # 2. Ringing
        yield {
            "type": "status_update",
            "call_id": call_id,
            "status": "RINGING",
            "message": "Line ringing, awaiting pickup...",
            "timestamp": time.time()
        }
        await asyncio.sleep(1.5)

        # 3. Connected
        yield {
            "type": "status_update",
            "call_id": call_id,
            "status": "CONNECTED",
            "message": "Call connected — CALL-E Voice Agent actively negotiating.",
            "timestamp": time.time()
        }
        await asyncio.sleep(0.8)

        # Scenario according to target type
        if target_type == "supplier":
            base_price = 4.25 if "tile" in requirement_name.lower() or "floor" in requirement_name.lower() else (
                60.0 if "paint" in requirement_name.lower() else (
                    19.50 if "light" in requirement_name.lower() or "led" in requirement_name.lower() else 175.0
                )
            )
            
            if "Supplier A" in target_name:
                unit_price = round(base_price * 1.12, 2)
                stock = max(quantity + 50, 550.0)
                discount = 0.0
                lead_days = 1
                deliv_ok = True
                deliv_cost = 45.0
            elif "Supplier C" in target_name:
                unit_price = round(base_price * 0.92, 2)
                stock = quantity
                discount = 0.0
                lead_days = 10
                deliv_ok = False
                deliv_cost = 0.0
            else: # Supplier B or default
                unit_price = base_price
                stock = max(quantity + 130, 650.0)
                discount = 5.0
                lead_days = 3
                deliv_ok = True
                deliv_cost = 0.0

            dialogue = [
                ("AI", f"Hello, I'm calling from ContractorPilot on behalf of our residential remodel in {project_location}. Do you have {quantity} {unit} of {requirement_name} in stock?"),
                ("Contact", f"Hi there! Yes, we currently have {int(stock)} {unit} in stock ready for dispatch."),
                ("AI", f"Great. What is your contractor price per {unit}, and can you handle jobsite delivery?"),
                ("Contact", f"List is ${unit_price:.2f} per {unit}.{' For an order of ' + str(quantity) + ' ' + unit + ', we can apply a 5% trade discount.' if discount > 0 else ''} We can deliver in {lead_days} business days {'via our freight truck' if deliv_ok else 'for depot pickup'}."),
                ("AI", f"Understood: ${unit_price:.2f} per {unit}, {int(discount)}% volume discount, {lead_days}-day delivery. Thank you for the quick quote!"),
                ("Contact", "You're very welcome! Feel free to reach back when you're ready to order.")
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
                "terms_notes": "Live commercial offer confirmed and verified by autonomous CALL-E agent."
            }

        else: # tradesperson
            daily_rate = 425.0 if "til" in requirement_name.lower() else (
                360.0 if "paint" in requirement_name.lower() else (
                    490.0 if "plumb" in requirement_name.lower() else 480.0
                )
            )
            est_days = int(quantity)

            dialogue = [
                ("AI", f"Hello {target_name}, I'm calling from ContractorPilot regarding an upcoming remodel in {project_location}. Would you be available for {requirement_name} ({quantity} {unit})?"),
                ("Contact", f"Hi! Yes, I have open availability starting early next week. What's the scope of work?"),
                ("AI", f"We need an estimated {quantity} {unit} on a luxury residence. What is your day rate and expected turnaround?"),
                ("Contact", f"My contractor rate for that scope is ${int(daily_rate):,} per {unit}. I can mobilize within 2 business days and finish in {est_days} working days with my professional crew and dust protection."),
                ("AI", f"Perfect: ${int(daily_rate):,} per {unit}, mobilization in 2 days, and completion in {est_days} days. Thank you so much."),
                ("Contact", "Sounds great, send over the site details whenever ready.")
            ]

            extracted = {
                "tradesperson_name": target_name,
                "trade": requirement_name,
                "unit_price": daily_rate,
                "is_available": True,
                "available_date": "Within 2 business days",
                "estimated_duration_days": est_days,
                "terms_notes": "Licensed subcontractor, full dust extraction equipment and surface protection provided."
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

        # 4. Structured extraction ready
        yield {
            "type": "extraction_ready",
            "call_id": call_id,
            "extracted_data": extracted,
            "timestamp": time.time()
        }
        await asyncio.sleep(0.5)

        # 5. Call completed
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
