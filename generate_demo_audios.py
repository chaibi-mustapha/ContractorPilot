"""
ContractorPilot - Demo Audio Generator
Generates realistic, expressive human voices (female and male) for suppliers and subcontractors,
plus full two-way phone dialogue simulations with CALL-E's autonomous voice agent.
Uses Microsoft Azure Neural Voices via edge-tts (ultra-realistic, natural inflection & breathing).
"""

import asyncio
import json
import os
from pathlib import Path
import edge_tts

OUTPUT_DIR = Path(__file__).parent / "frontend" / "audio"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------
# 1. Voice Definition Catalog
# ---------------------------------------------------------
# AI Agent Voice:
VOICE_CALLE_AGENT = "en-US-AndrewNeural"  # Professional, courteous, articulate autonomous voice AI

# Individual Audio Clips
AUDIO_ITEMS = [
    # --- SUPPLIERS (FOURNISSEURS) ---
    {
        "id": "sup_apex_tile_sarah",
        "filename": "supplier_apex_tile_sarah.mp3",
        "title": "Apex Tile & Stone — Sarah Jenkins (Account Rep)",
        "role": "Supplier - Wholesale Tile & Stone",
        "gender": "Female",
        "speaker": "Sarah Jenkins",
        "voice": "en-US-JennyNeural",
        "trade": "Flooring & Porcelain Tile",
        "text": (
            "Apex Tile and Stone, Sarah speaking! Hey, absolutely. We've got five pallets of the "
            "twenty-four by twenty-four Calacatta porcelain in stock right now at our central depot. "
            "For five hundred and twenty square feet, our wholesale contractor rate is four dollars and "
            "twenty cents per square foot. And since you're ordering over five hundred square feet, we can waive "
            "the delivery fee and have our flatbed truck drop it directly on your jobsite within forty-eight hours. "
            "I'll flag this under ContractorPilot's trade account. Do you also need modified thinset or leveling clips with that?"
        )
    },
    {
        "id": "sup_sherwin_paint_mark",
        "filename": "supplier_sherwin_paint_mark.mp3",
        "title": "Sherwin ProFinish — Mark Stevens (Pro Counter Desk)",
        "role": "Supplier - Commercial Paint & Coatings",
        "gender": "Male",
        "speaker": "Mark Stevens",
        "voice": "en-US-GuyNeural",
        "trade": "Paint & Interior Finishes",
        "text": (
            "Sherwin ProFinish, this is Mark at the contractor desk. Yeah, I can help you with that! "
            "We've got plenty of our Ultra Durable velvet matte interior finish in stock. In that Alabaster tone, "
            "ten gallons comes out to fifty-eight dollars a gallon on your commercial volume tier. That saves you about "
            "seven bucks a gallon off regular list price. I can tint and mix all ten gallons right now, and they'll be sitting "
            "on the will-call shelf by two PM today, or we can send our courier out to the jobsite first thing tomorrow morning."
        )
    },
    {
        "id": "sup_metro_lighting_emily",
        "filename": "supplier_metro_lighting_emily.mp3",
        "title": "Metro Lighting & Electric — Emily Carter (Distribution Lead)",
        "role": "Supplier - Electrical Fixtures & Lighting",
        "gender": "Female",
        "speaker": "Emily Carter",
        "voice": "en-US-AriaNeural",
        "trade": "Electrical & LED Downlights",
        "text": (
            "Good morning, Metro Lighting and Electric, Emily speaking! Yes, we have those seven-watt dimmable "
            "recessed LED downlights in three thousand K warm white. We keep hundreds on hand. For a box of twenty-four units, "
            "I can do nineteen dollars and fifty cents per fixture, and that includes the junction box and dimmable driver. "
            "If you get the purchase order confirmed before noon, we can ship them out today, and they'll arrive at your jobsite "
            "tomorrow morning via direct ground freight. Would you like me to hold twenty-four units for you?"
        )
    },
    {
        "id": "sup_prestige_plumbing_brian",
        "filename": "supplier_prestige_plumbing_brian.mp3",
        "title": "Prestige Bath & Fixtures — Brian Miller (Showroom Director)",
        "role": "Supplier - Sanitary & Luxury Bath Plumbing",
        "gender": "Male",
        "speaker": "Brian Miller",
        "voice": "en-US-ChristopherNeural",
        "trade": "Plumbing & Faucet Fixtures",
        "text": (
            "Prestige Bath and Plumbing, Brian speaking. Yes, for the luxury condo remodel! "
            "We have both the brushed brass gooseneck kitchen faucets and the thermostatic shower valve kits in stock. "
            "Our contractor package price is one hundred and eighty-five dollars for the kitchen faucet and two hundred "
            "and twenty dollars for the shower valve assembly. Both come with a full five-year commercial finish warranty. "
            "We can deliver directly to the jobsite on Thursday morning with zero freight charge. Sound good?"
        )
    },
    {
        "id": "sup_atlas_porcelain_lisa",
        "filename": "supplier_atlas_porcelain_lisa.mp3",
        "title": "Atlas Porcelain Warehouse — Lisa Vance (Sales Specialist)",
        "role": "Supplier - Alternative Tile Distributor",
        "gender": "Female",
        "speaker": "Lisa Vance",
        "voice": "en-US-MichelleNeural",
        "trade": "Alternative Flooring Offer",
        "text": (
            "Atlas Porcelain Warehouse, Lisa speaking. Thanks for checking with us! "
            "Yes, we carry a very similar rectified Italian porcelain tile in twenty-four by twenty-four. We currently have "
            "seven hundred square feet in stock in lot number forty-two. Our standard wholesale rate is four dollars and sixty cents "
            "per square foot, and we can deliver this Friday afternoon for a flat forty-dollar dispatch fee. If you're ready to take "
            "all five hundred and twenty square feet today, I can trim an extra five percent off the ticket."
        )
    },

    # --- ARTISANS & SUBCONTRACTORS (SOUS-TRAITANTS) ---
    {
        "id": "artisan_marcus_master_tiler",
        "filename": "artisan_marcus_master_tiler.mp3",
        "title": "Marcus Reed — Master Tile Setter",
        "role": "Subcontractor - Tiling & Bath Masonry",
        "gender": "Male",
        "speaker": "Marcus Reed",
        "voice": "en-US-EricNeural",
        "trade": "Master Tiler",
        "text": (
            "Hey, Marcus here! Yeah, I got your message about the Miller Residence condo remodel. "
            "Five hundred and twenty square feet of large format porcelain, covering the kitchen floor and the curbless master shower? "
            "Yeah, I can definitely take that on. My day rate is four hundred and twenty-five dollars. For that layout with the substrate leveling "
            "and the shower pan slope, it's about four days of solid work. I bring my own wet saws, laser levels, and HEPA dust containment tarps. "
            "I can lock you into my schedule starting next Tuesday. Text me the gate code and we're good to go."
        )
    },
    {
        "id": "artisan_david_finish_painter",
        "filename": "artisan_david_finish_painter.mp3",
        "title": "David Chen — Master Finish Painter",
        "role": "Subcontractor - Painting & Surface Prep",
        "gender": "Male",
        "speaker": "David Chen",
        "voice": "en-US-SteffanNeural",
        "trade": "Finish Painter",
        "text": (
            "Hello, this is David Chen Painting returning your call! Yes, for the living room and hallway walls and ceilings, "
            "ten gallons of velvet matte paint with trim detailing. I've estimated three full working days to do proper masking, patching, "
            "and two clean coats. My rate is three hundred and sixty dollars a day. We keep the jobsite spotless every evening and use "
            "low-dust sanding gear. I can start on Monday morning at eight AM sharp. Looking forward to working with ContractorPilot on this remodel."
        )
    },
    {
        "id": "artisan_anthony_electrician",
        "filename": "artisan_anthony_electrician.mp3",
        "title": "Anthony Brooks — Master Electrician",
        "role": "Subcontractor - Electrical & Automation",
        "gender": "Male",
        "speaker": "Anthony Brooks",
        "voice": "en-US-GuyNeural",
        "trade": "Master Electrician",
        "text": (
            "Anthony Brooks Electrical here. Yeah, twenty-four recessed LED fixtures plus the dimmable switch circuits in the living room "
            "and kitchen island. That's a two-day job for me and my apprentice. My day rate is four hundred and forty dollars. We're fully licensed, "
            "bonded, and insured, and we pull the local permit and coordinate the electrical rough-in inspection. I have an opening on my calendar "
            "next Wednesday. Let's do it."
        )
    },
    {
        "id": "artisan_james_plumber",
        "filename": "artisan_james_plumber.mp3",
        "title": "James Wilson — Licensed Master Plumber",
        "role": "Subcontractor - Plumbing & Sanitary Rough-in",
        "gender": "Male",
        "speaker": "James Wilson",
        "voice": "en-US-BrianNeural",
        "trade": "Licensed Plumber",
        "text": (
            "James Wilson Plumbing. Hey, thanks for calling. For the kitchen undermount sink rough-in and the curbless master shower linear drain "
            "installation, I'll need two working days. My rate is four hundred and fifty dollars a day. We pressure test all supply lines and water-test "
            "the shower pan before drywall goes up. I can be on site Friday morning. Let me know if the rough-in schedule is confirmed on your end."
        )
    },
    {
        "id": "artisan_elena_bath_specialist",
        "filename": "artisan_elena_bath_specialist.mp3",
        "title": "Elena Rodriguez — Tile & Waterproofing Specialist",
        "role": "Subcontractor - Bathroom & Waterproofing Specialist",
        "gender": "Female",
        "speaker": "Elena Rodriguez",
        "voice": "en-US-AvaNeural",
        "trade": "Bathroom Tile & Waterproofing",
        "text": (
            "Hi, this is Elena Rodriguez with Rodriguez Tile and Waterproofing. I'm calling back regarding the bathroom remodel! "
            "I specialize in Schluter waterproof membranes and curbless walk-in showers. For the bathroom walls, shower pan, and vanity backsplash, "
            "my rate is four hundred dollars a day, and it's a three-day scope. I provide a ten-year written warranty against any moisture infiltration. "
            "I have an opening starting next Thursday. Let me know if you want to book those dates!"
        )
    }
]

# ---------------------------------------------------------
# 2. Two-Way Phone Dialogues (CALL-E AI + Human)
# ---------------------------------------------------------
TWO_WAY_DIALOGUES = [
    {
        "id": "dialog_calle_and_apex_tile",
        "filename": "dialog_calle_and_apex_tile.mp3",
        "title": "CALL-E Calling Apex Tile & Stone (520 sq ft Porcelain)",
        "description": "Autonomous AI agent CALL-E calls Apex Tile, negotiates $4.20/sq ft wholesale price and free jobsite delivery.",
        "script": [
            {
                "speaker": "Sarah Jenkins (Supplier)",
                "voice": "en-US-JennyNeural",
                "text": "Apex Tile and Stone, Sarah speaking. How can I help you today?"
            },
            {
                "speaker": "CALL-E (AI Agent)",
                "voice": VOICE_CALLE_AGENT,
                "text": "Hello Sarah! This is CALL-E, autonomous procurement copilot for ContractorPilot. We are sourcing five hundred and twenty square feet of twenty-four by twenty-four Calacatta porcelain floor tiles for an active condo remodel in Metro Area. Do you have that in stock, and what is your best contractor rate?"
            },
            {
                "speaker": "Sarah Jenkins (Supplier)",
                "voice": "en-US-JennyNeural",
                "text": "Hi CALL-E! Yes, we have five pallets ready in our warehouse. For five hundred and twenty square feet, our wholesale rate is four dollars and twenty cents per square foot, down from four fifty. And we'll deliver it to the jobsite in forty-eight hours with no freight charge."
            },
            {
                "speaker": "CALL-E (AI Agent)",
                "voice": VOICE_CALLE_AGENT,
                "text": "That's fantastic. Four dollars and twenty cents per square foot with free jobsite delivery confirmed. I have captured your quote and added it to our master project proposal. Thank you, Sarah!"
            },
            {
                "speaker": "Sarah Jenkins (Supplier)",
                "voice": "en-US-JennyNeural",
                "text": "You got it! I've reserved the lot for ContractorPilot. Have a great day!"
            }
        ]
    },
    {
        "id": "dialog_calle_and_marcus_tiler",
        "filename": "dialog_calle_and_marcus_tiler.mp3",
        "title": "CALL-E Calling Marcus Reed (Master Tiler)",
        "description": "Autonomous AI agent CALL-E calls Marcus Reed to schedule 4 days of tile installation @ $425/day.",
        "script": [
            {
                "speaker": "Marcus Reed (Tiler)",
                "voice": "en-US-EricNeural",
                "text": "Marcus Reed here. What project do you have for me?"
            },
            {
                "speaker": "CALL-E (AI Agent)",
                "voice": VOICE_CALLE_AGENT,
                "text": "Hi Marcus! CALL-E calling on behalf of ContractorPilot. We have a five hundred and twenty square foot porcelain tile scope for the Miller Residence remodel, including kitchen floors and a curbless master shower. What is your current day rate and estimated duration?"
            },
            {
                "speaker": "Marcus Reed (Tiler)",
                "voice": "en-US-EricNeural",
                "text": "Sounds like a solid job. My day rate is four hundred and twenty-five dollars. For that layout with the shower pan slope and leveling, I'll need four days. I can start next Tuesday."
            },
            {
                "speaker": "CALL-E (AI Agent)",
                "voice": VOICE_CALLE_AGENT,
                "text": "Perfect. Four days at four hundred and twenty-five dollars per day, starting next Tuesday. I've logged your terms into the project schedule and cost sheet. Thanks Marcus!"
            },
            {
                "speaker": "Marcus Reed (Tiler)",
                "voice": "en-US-EricNeural",
                "text": "Awesome. Text me the jobsite address and lockbox code on Monday. Catch you later!"
            }
        ]
    },
    {
        "id": "dialog_calle_and_sherwin_paint",
        "filename": "dialog_calle_and_sherwin_paint.mp3",
        "title": "CALL-E Calling Sherwin ProFinish (10 Gal Paint)",
        "description": "Autonomous AI agent CALL-E negotiates $58/gal contractor price for 10 gallons velvet matte paint.",
        "script": [
            {
                "speaker": "Mark Stevens (Supplier)",
                "voice": "en-US-GuyNeural",
                "text": "Sherwin ProFinish, Mark speaking at the contractor desk."
            },
            {
                "speaker": "CALL-E (AI Agent)",
                "voice": VOICE_CALLE_AGENT,
                "text": "Hello Mark, CALL-E here from ContractorPilot. We need ten gallons of Ultra Durable velvet matte interior paint in Alabaster tone for an interior remodel. Can you confirm stock and your wholesale contractor price?"
            },
            {
                "speaker": "Mark Stevens (Supplier)",
                "voice": "en-US-GuyNeural",
                "text": "Hey CALL-E! Yep, plenty in stock. On your pro account, that's fifty-eight dollars a gallon, saving you about seven dollars a gallon. I can have all ten gallons tinted and ready for will-call pickup by two PM today, or courier delivery tomorrow morning."
            },
            {
                "speaker": "CALL-E (AI Agent)",
                "voice": VOICE_CALLE_AGENT,
                "text": "Confirmed at fifty-eight dollars per gallon for ten gallons. I have logged this offer in our procurement system. Thank you Mark!"
            },
            {
                "speaker": "Mark Stevens (Supplier)",
                "voice": "en-US-GuyNeural",
                "text": "Anytime! It'll be labeled under ContractorPilot at the counter. Have a good one!"
            }
        ]
    },
    {
        "id": "dialog_calle_and_elena_artisan",
        "filename": "dialog_calle_and_elena_artisan.mp3",
        "title": "CALL-E Calling Elena Rodriguez (Waterproofing Specialist)",
        "description": "Autonomous AI agent CALL-E consults Elena Rodriguez for bathroom waterproofing and curbless shower scope.",
        "script": [
            {
                "speaker": "Elena Rodriguez (Artisan)",
                "voice": "en-US-AvaNeural",
                "text": "Elena Rodriguez Tile and Waterproofing, how can I help?"
            },
            {
                "speaker": "CALL-E (AI Agent)",
                "voice": VOICE_CALLE_AGENT,
                "text": "Hi Elena! This is CALL-E from ContractorPilot. We have a master bathroom remodel requiring full waterproof membrane and curbless shower prep. What is your day rate and availability?"
            },
            {
                "speaker": "Elena Rodriguez (Artisan)",
                "voice": "en-US-AvaNeural",
                "text": "Hi! For curbless waterproofing and walls, my rate is four hundred dollars a day. It's a three-day scope, and I provide a ten-year moisture warranty. I can start next Thursday."
            },
            {
                "speaker": "CALL-E (AI Agent)",
                "voice": VOICE_CALLE_AGENT,
                "text": "Noted: three days at four hundred dollars a day with ten-year warranty, starting next Thursday. Terms captured and scored in our proposal builder. Thank you, Elena!"
            },
            {
                "speaker": "Elena Rodriguez (Artisan)",
                "voice": "en-US-AvaNeural",
                "text": "Perfect! Looking forward to working with ContractorPilot. Bye!"
            }
        ]
    }
]


async def generate_single_audio(item: dict) -> None:
    dest_path = OUTPUT_DIR / item["filename"]
    print(f"[*] Generating: {item['filename']} ({item['gender']}, Voice: {item['voice']})...")
    communicate = edge_tts.Communicate(item["text"], item["voice"])
    await communicate.save(str(dest_path))
    size_kb = dest_path.stat().st_size / 1024
    print(f"    -> OK: {dest_path.name} ({size_kb:.1f} KB)")


async def generate_dialogue_audio(dialog: dict) -> None:
    """Generates dialogue by generating individual turn MP3 bytes and concatenating them."""
    dest_path = OUTPUT_DIR / dialog["filename"]
    print(f"[*] Generating Dialogue: {dialog['filename']} ({len(dialog['script'])} turns)...")
    
    combined_bytes = bytearray()
    for idx, turn in enumerate(dialog["script"]):
        communicate = edge_tts.Communicate(turn["text"], turn["voice"])
        turn_bytes = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                turn_bytes.extend(chunk["data"])
        combined_bytes.extend(turn_bytes)
        # Add small pause between turns by generating a tiny silence or direct continuation
        # (Direct concatenation of edge-tts MP3 frames produces smooth, natural turn-taking)

    with open(dest_path, "wb") as f:
        f.write(combined_bytes)
    
    size_kb = dest_path.stat().st_size / 1024
    print(f"    -> OK Dialogue: {dest_path.name} ({size_kb:.1f} KB)")


async def main():
    print("==================================================================")
    print("  ContractorPilot - Autonomous Voice & Audio Studio Generator     ")
    print(f"  Target Directory: {OUTPUT_DIR}")
    print("==================================================================")
    
    # 1. Generate Individual Clips
    print("\n--- Phase 1: Generating Individual Supplier & Artisan Voices ---")
    for item in AUDIO_ITEMS:
        await generate_single_audio(item)

    # 2. Generate Full Two-Way Dialogues
    print("\n--- Phase 2: Generating 2-Way Dialogues (CALL-E AI + Human) ---")
    for dialog in TWO_WAY_DIALOGUES:
        await generate_dialogue_audio(dialog)

    # 3. Create Manifest JSON
    manifest = {
        "title": "ContractorPilot Audio Demonstration Catalog",
        "description": "Ultra-realistic neural human voices (male & female) for Devpost demonstration video & in-app live audio preview.",
        "individual_voices": AUDIO_ITEMS,
        "dialogues": TWO_WAY_DIALOGUES,
        "total_tracks": len(AUDIO_ITEMS) + len(TWO_WAY_DIALOGUES)
    }

    manifest_path = OUTPUT_DIR / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"\n[+] Manifest saved to: {manifest_path}")

    print("\n==================================================================")
    print("  ALL DEMO AUDIOS GENERATED SUCCESSFULLY!                         ")
    print("==================================================================")


if __name__ == "__main__":
    asyncio.run(main())
