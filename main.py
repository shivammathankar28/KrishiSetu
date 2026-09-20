import json
import os
import uuid
import hashlib
import secrets
import io
import csv
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
from contextlib import asynccontextmanager

import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from twilio.rest import Client
from fastapi.middleware.cors import CORSMiddleware

# ---------------------------------------------------------
# SQLITE DATABASE & SECURITY STATE PERSISTENCE 
# ---------------------------------------------------------
DB_FILE = "krishisetu.db"

def init_sqlite_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create tables for state persistence
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS active_tokens (
            token_id TEXT PRIMARY KEY,
            data TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registered_farmers (
            phone_number TEXT PRIMARY KEY,
            data TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS slot_occupancy (
            slot_name TEXT PRIMARY KEY,
            occupancy REAL
        )
    ''')
    
    # Initialize default slots if empty
    slots = ["08:00 - 10:00", "10:00 - 12:00", "12:00 - 14:00", "14:00 - 16:00"]
    for slot in slots:
        cursor.execute("INSERT OR IGNORE INTO slot_occupancy (slot_name, occupancy) VALUES (?, ?)", (slot, 0.0))
        
    conn.commit()
    conn.close()

init_sqlite_db()

OFFICER_CREDENTIALS_HASH = hashlib.sha256("admin123".encode()).hexdigest()
active_officer_sessions: Dict[str, bool] = {}
security = HTTPBearer()

def require_officer(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    if token not in active_officer_sessions:
        raise HTTPException(status_code=401, detail="Unauthorized. Session expired or invalid.")
    return True

active_tokens: Dict[str, dict] = {}
registered_farmers: Dict[str, dict] = {}
pending_otps: Dict[str, str] = {}

MANDI_CONFIG = {
    "name": "DoCA APMC Central Procurement Hub (Nagpur Yard 01)",
    "slot_capacity_quintals": 120.0,
    "slots": ["08:00 - 10:00", "10:00 - 12:00", "12:00 - 14:00", "14:00 - 16:00"],
    "procurement_centers": [
        "Nagpur Central APMC Yard 01",
        "Hingna Sub-Yard 02",
        "Butibori Agro Hub 03"
    ],
    "msp_rates": {
        "Soybean": 4892.00,
        "Wheat": 2275.00,
        "Paddy (Rice)": 2300.00,
        "Cotton": 7121.00
    },
    "stock_targets": {
        "Soybean": {"target_quota_qtl": 2500.0, "procured_qtl": 1420.0},
        "Wheat": {"target_quota_qtl": 5000.0, "procured_qtl": 3680.0},
        "Paddy (Rice)": {"target_quota_qtl": 4000.0, "procured_qtl": 2100.0},
        "Cotton": {"target_quota_qtl": 1800.0, "procured_qtl": 950.0}
    }
}
slot_occupancy: Dict[str, float] = {slot: 0.0 for slot in MANDI_CONFIG["slots"]}

def load_state():
    global active_tokens, registered_farmers, slot_occupancy
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT token_id, data FROM active_tokens")
        for row in cursor.fetchall():
            active_tokens[row[0]] = json.loads(row[1])
            
        cursor.execute("SELECT phone_number, data FROM registered_farmers")
        for row in cursor.fetchall():
            registered_farmers[row[0]] = json.loads(row[1])
            
        cursor.execute("SELECT slot_name, occupancy FROM slot_occupancy")
        for row in cursor.fetchall():
            slot_occupancy[row[0]] = row[1]
            
        conn.close()
    except Exception as e:
        print(f"Error loading state from SQLite: {e}")

def save_state():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Save tokens
        cursor.execute("DELETE FROM active_tokens")
        for tid, tdata in active_tokens.items():
            cursor.execute("INSERT INTO active_tokens (token_id, data) VALUES (?, ?)", (tid, json.dumps(tdata)))
            
        # Save farmers
        cursor.execute("DELETE FROM registered_farmers")
        for fphone, fdata in registered_farmers.items():
            cursor.execute("INSERT INTO registered_farmers (phone_number, data) VALUES (?, ?)", (fphone, json.dumps(fdata)))
            
        # Save slot occupancy
        for slot_name, occ in slot_occupancy.items():
            cursor.execute("INSERT OR REPLACE INTO slot_occupancy (slot_name, occupancy) VALUES (?, ?)", (slot_name, occ))
            
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error saving state to SQLite: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_state()
    yield
    save_state()

app = FastAPI(title="SIH 26032 - Full APMC Procurement Hub", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# TWILIO WHATSAPP CONFIGURATION
# ---------------------------------------------------------
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "YOUR_TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "YOUR_TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"

def send_whatsapp_message(to_phone: str, message_body: str):
    try:
        if "YOUR_TWILIO" in TWILIO_ACCOUNT_SID:
            print(f"\n[WHATSAPP ALERT SIMULATOR] >>> To: {to_phone}\n{message_body}\n" + "-"*50)
            return

        clean_phone = to_phone.strip().replace(" ", "").replace("-", "")
        if not clean_phone.startswith("+"):
            clean_phone = f"+91{clean_phone}" if len(clean_phone) == 10 else f"+{clean_phone}"

        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(from_=TWILIO_WHATSAPP_NUMBER, body=message_body, to=f"whatsapp:{clean_phone}")
    except Exception as e:
        pass

STAGES = [
    "REQUESTED",
    "OFFICER_ACCEPTED",
    "GATE_IN",
    "ASSAYING",
    "WEIGHMENT",
    "UNLOADING",
    "PAYMENT_PROCESSING",
    "COMPLETED"
]

# ---------------------------------------------------------
# PYDANTIC SCHEMAS
# ---------------------------------------------------------
class LoginRequest(BaseModel):
    password: str

class SendOTPRequest(BaseModel):
    phone_number: str
    farmer_name: str

class VerifyOTPRequest(BaseModel):
    phone_number: str
    otp_code: str

class FarmerRegistrationRequest(BaseModel):
    farmer_name: str
    phone_number: str
    aadhaar_last_four: str
    bank_account_no: str
    ifsc_code: str
    land_area_acres: float
    village: str
    total_harvest_stock_qtl: float
    procurement_center: str

class SlotBookingRequest(BaseModel):
    farmer_phone: str
    commodity: str
    weight_to_bring_quintals: float
    vehicle_type: str
    vehicle_number: str
    preferred_slot: str

class OfficerDecisionRequest(BaseModel):
    token_id: str
    decision: str
    remarks: Optional[str] = "Approved for Mandi Gate Entry"

class TokenAdvanceRequest(BaseModel):
    token_id: str
    actual_weight: Optional[float] = None
    quality_status: Optional[str] = None
    quality_remarks: Optional[str] = None

class EmergencyDelayRequest(BaseModel):
    delay_minutes: int
    reason: str

# ---------------------------------------------------------
# WEBSOCKET DISPATCHER
# ---------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_state(self):
        total_market_arrivals = sum(float(t["weight_quintals"]) for t in active_tokens.values() if t["current_stage"] not in ["REQUESTED"])
        state = {
            "type": "STATE_UPDATE",
            "mandi": MANDI_CONFIG["name"],
            "procurement_centers": MANDI_CONFIG["procurement_centers"],
            "slot_occupancy": slot_occupancy,
            "max_capacity": float(MANDI_CONFIG["slot_capacity_quintals"]),
            "msp_rates": MANDI_CONFIG["msp_rates"],
            "stock_targets": MANDI_CONFIG["stock_targets"],
            "total_market_arrivals_today": round(total_market_arrivals, 2),
            "tokens": list(active_tokens.values()),
            "total_farmers": len(registered_farmers)
        }
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(state))
            except Exception:
                pass

manager = ConnectionManager()

# ---------------------------------------------------------
# REST API ENDPOINTS
# ---------------------------------------------------------
@app.post("/api/v1/officer/login")
async def officer_login(req: LoginRequest):
    hashed = hashlib.sha256(req.password.encode()).hexdigest()
    if hashed == OFFICER_CREDENTIALS_HASH:
        token = secrets.token_hex(16)
        active_officer_sessions[token] = True
        return {"status": "SUCCESS", "token": token}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/api/v1/farmer/send-otp")
async def send_farmer_otp(req: SendOTPRequest, background_tasks: BackgroundTasks):
    otp = "123456" if "9876543210" in req.phone_number else f"{secrets.randbelow(900000) + 100000}"
    pending_otps[req.phone_number] = otp
    
    otp_msg = f"🌾 *KrishiSetu Verification*\n\nDear {req.farmer_name},\nYour Login & Registration OTP code is: *{otp}*. Valid for 10 minutes."
    background_tasks.add_task(send_whatsapp_message, req.phone_number, otp_msg)
    return {"status": "SUCCESS", "message": "OTP sent successfully.", "debug_otp": otp}

@app.post("/api/v1/farmer/verify-otp")
async def verify_farmer_otp(req: VerifyOTPRequest):
    stored_otp = pending_otps.get(req.phone_number)
    if not stored_otp or stored_otp != req.otp_code:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP code.")
    
    pending_otps.pop(req.phone_number, None)
    return {"status": "SUCCESS", "message": "OTP verified successfully."}

@app.get("/api/v1/slots/available")
async def get_available_slots():
    slots = []
    for slot, occ in slot_occupancy.items():
        rem = float(MANDI_CONFIG["slot_capacity_quintals"]) - float(occ)
        if rem > 0:
            slots.append({"slot": slot, "space_left_qtl": round(rem, 2)})
    return {"status": "SUCCESS", "slots": slots}

@app.get("/api/v1/market/live-status")
async def get_live_market_status():
    return {
        "mandi": MANDI_CONFIG["name"],
        "procurement_centers": MANDI_CONFIG["procurement_centers"],
        "msp_rates": MANDI_CONFIG["msp_rates"],
        "stock_targets": MANDI_CONFIG["stock_targets"],
        "slot_occupancy": slot_occupancy,
        "active_tokens": len(active_tokens)
    }

@app.get("/api/v1/slots/status/{token_id}")
async def get_token_status(token_id: str):
    if token_id not in active_tokens:
        raise HTTPException(status_code=404, detail="Token not found.")
    return {"status": "SUCCESS", "token": active_tokens[token_id]}

@app.get("/api/v1/slots/queue-position/{token_id}")
async def get_queue_position(token_id: str):
    if token_id not in active_tokens:
        raise HTTPException(status_code=404, detail="Token not found.")
    current_token = active_tokens[token_id]
    allocated_slot = current_token["allocated_slot"]
    farmers_ahead = 0
    for t_id, tk in active_tokens.items():
        if (tk["allocated_slot"] == allocated_slot and 
            tk["officer_status"] == "ACCEPTED" and 
            tk["current_stage"] not in ["COMPLETED", "REJECTED"] and
            tk["created_at"] < current_token["created_at"]):
            farmers_ahead += 1
    avg_time_per_farmer = 12
    est_wait = (farmers_ahead * avg_time_per_farmer) + current_token.get("delay_offset_mins", 0)
    return {"status": "SUCCESS", "farmers_ahead": farmers_ahead, "estimated_wait_minutes": max(5, est_wait)}

@app.post("/api/v1/farmer/register")
async def register_farmer(req: FarmerRegistrationRequest):
    if len(req.phone_number.strip()) != 10 or not req.phone_number.isdigit():
        raise HTTPException(status_code=400, detail="⚠️ Validation Error: Mobile number must be exactly 10 digits.")
    if len(req.aadhaar_last_four.strip()) != 4 or not req.aadhaar_last_four.isdigit():
        raise HTTPException(status_code=400, detail="⚠️ Validation Error: Aadhaar must be exactly the last 4 digits.")
    if len(req.bank_account_no.strip()) < 9 or not req.bank_account_no.isdigit():
        raise HTTPException(status_code=400, detail="⚠️ Validation Error: Enter a valid bank account number.")
    if len(req.ifsc_code.strip()) != 11:
        raise HTTPException(status_code=400, detail="⚠️ Validation Error: IFSC code must be exactly 11 characters.")

    farmer_id = f"FARM-{uuid.uuid4().hex[:6].upper()}"
    registered_farmers[req.phone_number] = {
        "farmer_id": farmer_id,
        "farmer_name": req.farmer_name,
        "phone_number": req.phone_number,
        "aadhaar_last_four": req.aadhaar_last_four,
        "bank_account_no": req.bank_account_no,
        "ifsc_code": req.ifsc_code,
        "land_area_acres": req.land_area_acres,
        "village": req.village,
        "total_harvest_stock_qtl": float(req.total_harvest_stock_qtl),
        "stock_remaining_at_farm_qtl": float(req.total_harvest_stock_qtl),
        "procurement_center": req.procurement_center,
        "registered_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    save_state()
    await manager.broadcast_state()
    return {"status": "SUCCESS", "farmer": registered_farmers[req.phone_number]}

@app.post("/api/v1/slots/book")
async def book_slot(req: SlotBookingRequest, background_tasks: BackgroundTasks):
    if len(req.farmer_phone.strip()) != 10 or not req.farmer_phone.isdigit():
        raise HTTPException(status_code=400, detail="⚠️ Validation Error: Mobile number must be exactly 10 digits.")

    if req.farmer_phone not in registered_farmers:
        registered_farmers[req.farmer_phone] = {
            "farmer_id": f"FARM-{uuid.uuid4().hex[:6].upper()}",
            "farmer_name": "Suresh Kumar Verma",
            "phone_number": req.farmer_phone,
            "aadhaar_last_four": "1234",
            "bank_account_no": "918273645012",
            "ifsc_code": "SBIN0001234",
            "land_area_acres": 6.5,
            "village": "Hingna, Nagpur",
            "total_harvest_stock_qtl": 120.0,
            "stock_remaining_at_farm_qtl": 120.0,
            "procurement_center": "Nagpur Central APMC Yard 01",
            "registered_at": datetime.now().strftime("%Y-%m-%d %H:%M")
        }

    for tk in active_tokens.values():
        if tk["phone_number"] == req.farmer_phone and tk["current_stage"] not in ["COMPLETED", "REJECTED"]:
            raise HTTPException(status_code=400, detail="⚠️ Duplicate Booking Error: You already have an active pending or in-progress token in the system!")

    farmer = registered_farmers[req.farmer_phone]
    weight = float(req.weight_to_bring_quintals)

    if weight > farmer["stock_remaining_at_farm_qtl"]:
        raise HTTPException(status_code=400, detail=f"⚠️ Validation Error: Declared load ({weight} Qtl) exceeds your remaining farm stock!")

    current_booked = float(slot_occupancy.get(req.preferred_slot, 0.0))
    if current_booked + weight > MANDI_CONFIG["slot_capacity_quintals"]:
        raise HTTPException(status_code=409, detail=f"⚠️ Congestion Alert: Slot '{req.preferred_slot}' is saturated! Select another slot.")

    msp_rate = MANDI_CONFIG["msp_rates"].get(req.commodity, 2000.0)
    estimated_payout = round(msp_rate * weight, 2)
    token_id = f"TKN-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:5].upper()}"

    token_record = {
        "token_id": token_id,
        "farmer_id": farmer["farmer_id"],
        "farmer_name": farmer["farmer_name"],
        "phone_number": req.farmer_phone,
        "bank_account_no": farmer["bank_account_no"],
        "ifsc_code": farmer["ifsc_code"],
        "commodity": req.commodity,
        "total_farm_stock_qtl": float(farmer["total_harvest_stock_qtl"]),
        "weight_quintals": weight,
        "vehicle_type": req.vehicle_type,
        "vehicle_number": req.vehicle_number,
        "allocated_slot": req.preferred_slot,
        "procurement_center": farmer.get("procurement_center", "Nagpur Central APMC Yard 01"),
        "current_stage": "REQUESTED",
        "officer_status": "PENDING_APPROVAL",
        "officer_remarks": "Awaiting Procurement Officer Verification",
        "stage_index": 0,
        "estimated_payout_rs": estimated_payout,
        "payment_status": "PENDING_OFFICER_APPROVAL",
        "dbt_reference": "N/A",
        "quality_status": "PENDING",
        "quality_remarks": "N/A",
        "created_at": datetime.now().strftime("%H:%M:%S"),
        "estimated_wait_mins": 25,
        "delay_offset_mins": 0
    }

    active_tokens[token_id] = token_record
    slot_occupancy[req.preferred_slot] += weight
    farmer["stock_remaining_at_farm_qtl"] -= weight

    req_msg = (
        f"📋 *SIH-26032: Slot Request Submitted*\n\n"
        f"Farmer: *{farmer['farmer_name']}*\nToken: `{token_id}`\n"
        f"Crop: *{req.commodity}* ({weight} Qtl)\nSlot: *{req.preferred_slot}*\n"
        f"Center: *{token_record['procurement_center']}*\n"
        f"Status: ⏳ *Sent to Procurement Officer for Gate Approval*\n\n"
        f"You will receive your Digital QR Pass once approved."
    )
    background_tasks.add_task(send_whatsapp_message, req.farmer_phone, req_msg)

    save_state()
    await manager.broadcast_state()
    return {"status": "SUCCESS", "token": token_record}

@app.post("/api/v1/officer/decision")
async def officer_decision(req: OfficerDecisionRequest, background_tasks: BackgroundTasks, _auth: bool = Depends(require_officer)):
    if req.token_id not in active_tokens:
        raise HTTPException(status_code=404, detail="Token not found.")

    token = active_tokens[req.token_id]
    if token["officer_status"] != "PENDING_APPROVAL":
        raise HTTPException(status_code=400, detail="⚠️ Decision already logged.")

    if req.decision == "ACCEPT":
        token["current_stage"] = "OFFICER_ACCEPTED"
        token["officer_status"] = "ACCEPTED"
        token["officer_remarks"] = req.remarks or "Officer verified and approved gate entry."
        token["stage_index"] = 1
        token["payment_status"] = "AWAITING_PHYSICAL_INTAKE"

        appr_msg = (
            f"✅ *SIH-26032: Procurement Officer Approved Your Slot!*\n\n"
            f"Token ID: `{token['token_id']}`\nFarmer: *{token['farmer_name']}*\n"
            f"Slot Time: *{token['allocated_slot']}*\nCenter: *{token.get('procurement_center', MANDI_CONFIG['name'])}*\n"
            f"Est. Value: *₹{token['estimated_payout_rs']:,.2f}*\n\nGate pass is now active."
        )
        background_tasks.add_task(send_whatsapp_message, token["phone_number"], appr_msg)

    elif req.decision == "REJECT":
        token["current_stage"] = "REJECTED"
        token["officer_status"] = "REJECTED"
        token["officer_remarks"] = req.remarks or "Mandi quota saturated."
        weight = float(token["weight_quintals"])
        slot_occupancy[token["allocated_slot"]] = max(0.0, slot_occupancy[token["allocated_slot"]] - weight)

        if token["phone_number"] in registered_farmers:
            registered_farmers[token["phone_number"]]["stock_remaining_at_farm_qtl"] += weight

        rej_msg = (f"❌ *SIH-26032: Slot Request Rejected*\n\nToken: `{token['token_id']}`\nReason: *{token['officer_remarks']}*")
        background_tasks.add_task(send_whatsapp_message, token["phone_number"], rej_msg)

    save_state()
    await manager.broadcast_state()
    return {"status": "SUCCESS", "token": token}

@app.post("/api/v1/mandi/advance-stage")
async def advance_stage(req: TokenAdvanceRequest, background_tasks: BackgroundTasks, _auth: bool = Depends(require_officer)):
    if req.token_id not in active_tokens:
        raise HTTPException(status_code=404, detail="Token not found.")

    token = active_tokens[req.token_id]
    if token["current_stage"] == "COMPLETED":
        raise HTTPException(status_code=400, detail="⚠️ Token already completed.")

    if token["current_stage"] == "ASSAYING":
        if req.quality_status not in ["GOOD", "BAD"]:
            raise HTTPException(status_code=400, detail="Quality check status (GOOD or BAD) is required.")
        
        token["quality_status"] = req.quality_status
        token["quality_remarks"] = req.quality_remarks or ("Assaying passed: Good quality stock." if req.quality_status == "GOOD" else "Assaying failed: Substandard or wet stock.")

        if req.quality_status == "BAD":
            token["current_stage"] = "REJECTED"
            token["officer_status"] = "REJECTED"
            weight = float(token["weight_quintals"])
            slot_occupancy[token["allocated_slot"]] = max(0.0, slot_occupancy[token["allocated_slot"]] - weight)
            if token["phone_number"] in registered_farmers:
                registered_farmers[token["phone_number"]]["stock_remaining_at_farm_qtl"] += weight

            fail_msg = f"❌ *SIH-26032: Assaying Quality Check Failed*\n\nToken: `{token['token_id']}`\nReason: *{token['quality_remarks']}*\nStock returned to farm."
            background_tasks.add_task(send_whatsapp_message, token["phone_number"], fail_msg)
            save_state()
            await manager.broadcast_state()
            return {"status": "REJECTED", "token": token}

    if token["current_stage"] == "WEIGHMENT":
        if req.actual_weight is None or float(req.actual_weight) <= 0:
            raise HTTPException(status_code=400, detail="Actual verified weight must be declared at WEIGHMENT stage.")
        
        diff = float(req.actual_weight) - float(token["weight_quintals"])
        token["weight_quintals"] = float(req.actual_weight)
        slot_occupancy[token["allocated_slot"]] = max(0.0, slot_occupancy[token["allocated_slot"]] + diff)
        
        msp_rate = MANDI_CONFIG["msp_rates"].get(token["commodity"], 2000.0)
        token["estimated_payout_rs"] = round(msp_rate * float(token["weight_quintals"]), 2)

    curr_idx = token["stage_index"]
    if curr_idx < len(STAGES) - 1:
        token["stage_index"] += 1
        token["current_stage"] = STAGES[token["stage_index"]]

        if token["current_stage"] == "PAYMENT_PROCESSING":
            token["payment_status"] = "DBT_INITIATED"
            token["dbt_reference"] = f"DBT-DOCA-{datetime.now().strftime('%Y%m%d%H%M')}-{uuid.uuid4().hex[:4].upper()}"
            token["estimated_wait_mins"] = 5
        elif token["current_stage"] == "COMPLETED":
            token["payment_status"] = "PAYMENT_CREDITED"
            token["payment_credited_at"] = datetime.now().strftime("%d-%b-%Y %I:%M %p")
            token["estimated_wait_mins"] = 0
            weight = float(token["weight_quintals"])
            slot_occupancy[token["allocated_slot"]] = max(0.0, slot_occupancy[token["allocated_slot"]] - weight)

            crop = token["commodity"]
            if crop in MANDI_CONFIG["stock_targets"]:
                MANDI_CONFIG["stock_targets"][crop]["procured_qtl"] += weight

            pay_msg = (
                f"💰 *SIH-26032: MSP DBT Payment Credited!*\n\nFarmer: *{token['farmer_name']}*\n"
                f"Crop: *{token['commodity']}* ({token['weight_quintals']} Qtl)\nAmount Credited: *₹{token['estimated_payout_rs']:,.2f}*\n"
                f"A/C: *XXXX{token['bank_account_no'][-4:]}* ({token['ifsc_code']})\nDBT Ref: `{token['dbt_reference']}`"
            )
            background_tasks.add_task(send_whatsapp_message, token["phone_number"], pay_msg)
        else:
            token["estimated_wait_mins"] = max(5, token["estimated_wait_mins"] - 5)
            stage_msg = (f"🚜 *Mandi Queue Update*\n\nToken: `{token['token_id']}`\nCurrent Yard Station: *{token['current_stage']}*\nEst. Wait Time: ~{token['estimated_wait_mins']} Mins.")
            background_tasks.add_task(send_whatsapp_message, token["phone_number"], stage_msg)

    save_state()
    await manager.broadcast_state()
    return {"status": "UPDATED", "token": token}

@app.post("/api/v1/mandi/emergency-delay")
async def emergency_delay(req: EmergencyDelayRequest, background_tasks: BackgroundTasks, _auth: bool = Depends(require_officer)):
    for t_id, token in active_tokens.items():
        if token["current_stage"] not in ["COMPLETED", "REJECTED"]:
            token["delay_offset_mins"] += req.delay_minutes
            token["estimated_wait_mins"] += req.delay_minutes
            delay_msg = (
                f"⚠️ *APMC Urgent Delay Broadcast*\n\nDear {token['farmer_name']}, arrivals at {token.get('procurement_center', MANDI_CONFIG['name'])} "
                f"are shifted by *+{req.delay_minutes} mins* due to *{req.reason}*."
            )
            background_tasks.add_task(send_whatsapp_message, token["phone_number"], delay_msg)

    save_state()
    await manager.broadcast_state()
    return {"status": "APPLIED", "message": f"+{req.delay_minutes} min delay broadcasted."}

# ---------------------------------------------------------
# SECURE DOWNLOAD ENDPOINTS
# ---------------------------------------------------------
@app.get("/api/v1/downloads/officer/registry")
async def download_officer_registry(_auth: bool = Depends(require_officer)):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Token ID", "Procurement Center", "Allocated Slot", "Farmer Name", "Secure Mobile Number", "Commodity", "Weight (Qtl)", "Vehicle No", "Officer Decision Status", "Quality Status"])
    for tk in active_tokens.values():
        safe_phone = "*" * 6 + tk["phone_number"][-4:]
        writer.writerow([
            tk["token_id"], tk.get("procurement_center", "Nagpur Central APMC Yard 01"), tk["allocated_slot"], tk["farmer_name"], 
            safe_phone, tk["commodity"], tk["weight_quintals"], 
            tk["vehicle_number"], tk["officer_status"], tk.get("quality_status", "N/A")
        ])
    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=Encrypted_Slot_Registry.csv"})

@app.get("/api/v1/downloads/officer/ledger")
async def download_officer_ledger(_auth: bool = Depends(require_officer)):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Token ID", "Procurement Center", "Date", "Farmer Name", "Secure Bank A/C", "Commodity", "Verified Weight", "Total Payout (Rs)", "DBT Status", "Secure DBT Reference"])
    for tk in active_tokens.values():
        if tk["current_stage"] not in ["REQUESTED", "REJECTED"]:
            safe_acc = "*" * 8 + tk["bank_account_no"][-4:]
            safe_dbt = tk["dbt_reference"][:8] + "****" if tk["dbt_reference"] != "N/A" else "N/A"
            writer.writerow([
                tk["token_id"], tk.get("procurement_center", "Nagpur Central APMC Yard 01"), tk["created_at"], tk["farmer_name"], safe_acc, 
                tk["commodity"], tk["weight_quintals"], tk["estimated_payout_rs"], 
                tk["payment_status"], safe_dbt
            ])
    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=Encrypted_Transaction_Ledger.csv"})

@app.get("/api/v1/downloads/farmer/receipt/{token_id}")
async def download_farmer_receipt(token_id: str, phone: str):
    if token_id not in active_tokens:
        raise HTTPException(status_code=404, detail="Token not found")
    
    tk = active_tokens[token_id]
    if tk["phone_number"] != phone:
        raise HTTPException(status_code=403, detail="Unauthorized access.")
    
    receipt_text = f"""
===================================================================
                KRISHISETU - OFFICIAL DBT RECEIPT         
===================================================================
Timestamp:         {tk.get('payment_credited_at', tk['created_at'])}
Procurement Center:{tk.get('procurement_center', MANDI_CONFIG['name'])}

[ FARMER DETAILS ]
Name:              {tk['farmer_name']}
Mobile Number:     {tk['phone_number']}
Token ID:          {tk['token_id']}

[ PROCUREMENT & ASSAYING DETAILS ]
Commodity:         {tk['commodity']}
Quality Check:     {tk.get('quality_status', 'PASSED')}
Verified Weight:   {tk['weight_quintals']} Quintals
Vehicle Number:    {tk['vehicle_number']}
Allotted Slot:     {tk['allocated_slot']}

[ FINANCIAL & BANKING SETTLEMENT ]
Total Payout:      Rs. {tk['estimated_payout_rs']:,.2f}
Settlement Status: {tk['payment_status']}
Target Account:    {tk['bank_account_no']}
IFSC Code:         {tk['ifsc_code']}
DBT Reference:     {tk['dbt_reference']}

===================================================================
* This is a computer generated document. No signature is required.
===================================================================
    """
    output = io.StringIO(receipt_text)
    return StreamingResponse(output, media_type="text/plain", headers={"Content-Disposition": f"attachment; filename=Payment_Receipt_{token_id}.txt"})

# ---------------------------------------------------------
# WEBSOCKET ROUTE
# ---------------------------------------------------------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    await manager.broadcast_state()
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ---------------------------------------------------------
# FULL MULTI-TAB DASHBOARD WITH FULL LOCALIZATION (RAW STRING)
# ---------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    return r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KrishiSetu</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
</head>
<body class="bg-slate-100 font-sans text-slate-800">

    <!-- VALIDATION & ERROR ALERT MODAL -->
    <div id="validationAlertModal" class="fixed inset-0 bg-slate-900/80 z-[150] flex items-center justify-center hidden">
        <div class="bg-white p-6 rounded-2xl shadow-2xl max-w-sm w-full space-y-4 border-t-4 border-red-600 text-center">
            <div class="w-12 h-12 bg-red-100 text-red-600 rounded-full flex items-center justify-center mx-auto text-xl">
                <i class="fa-solid fa-triangle-exclamation"></i>
            </div>
            <h3 class="font-bold text-slate-900 text-base" id="alertTitle">Invalid Input Error</h3>
            <p class="text-xs text-slate-600 leading-relaxed" id="alertMessage">Please check your inputs.</p>
            <button onclick="closeValidationAlert()" class="w-full bg-slate-900 hover:bg-black text-white font-bold py-2.5 rounded-xl text-xs transition">
                Got It & Fix
            </button>
        </div>
    </div>

    <!-- ASSAYING QUALITY CHECK MODAL -->
    <div id="qualityModal" class="fixed inset-0 bg-slate-900/80 z-[120] flex items-center justify-center hidden">
        <div class="bg-white p-6 rounded-2xl shadow-2xl max-w-md w-full space-y-4">
            <div class="flex justify-between items-center pb-3 border-b">
                <h3 class="font-bold text-slate-900 text-base" data-i18n="assay_title"><i class="fa-solid fa-flask-vial text-emerald-600 mr-2"></i>Assaying Quality Inspection</h3>
                <button onclick="closeQualityModal()" class="text-slate-400 hover:text-slate-600 text-lg font-bold">&times;</button>
            </div>
            <p class="text-xs text-slate-600"><span data-i18n="assay_desc">Inspect moisture, purity, and grain standards for token</span> <span id="qualityModalToken" class="font-mono font-bold text-emerald-800"></span>.</p>
            <div class="space-y-3 pt-2">
                <div>
                    <label class="text-xs font-semibold text-slate-700" data-i18n="assay_lbl_remarks">Inspection Result / Remarks</label>
                    <input type="text" id="qualityRemarksInput" placeholder="e.g., Moisture within 12% limit, clean grains" value="Standard quality parameters met." class="w-full border rounded-lg p-2.5 text-xs mt-1">
                </div>
                <div class="grid grid-cols-2 gap-3 pt-2">
                    <button onclick="submitQualityCheck('GOOD')" class="bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-2.5 rounded-xl text-xs transition flex items-center justify-center space-x-1">
                        <i class="fa-solid fa-circle-check"></i><span data-i18n="assay_btn_good">Good (Pass & Forward)</span>
                    </button>
                    <button onclick="submitQualityCheck('BAD')" class="bg-red-600 hover:bg-red-700 text-white font-bold py-2.5 rounded-xl text-xs transition flex items-center justify-center space-x-1">
                        <i class="fa-solid fa-circle-xmark"></i><span data-i18n="assay_btn_bad">Bad (Reject Stock)</span>
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- WEIGHMENT FINAL WEIGHT MODAL -->
    <div id="weighmentModal" class="fixed inset-0 bg-slate-900/80 z-[120] flex items-center justify-center hidden">
        <div class="bg-white p-6 rounded-2xl shadow-2xl max-w-md w-full space-y-4">
            <div class="flex justify-between items-center pb-3 border-b">
                <h3 class="font-bold text-slate-900 text-base" data-i18n="weigh_title"><i class="fa-solid fa-scale-balanced text-amber-600 mr-2"></i>Weighbridge Final Measurement</h3>
                <button onclick="closeWeighmentModal()" class="text-slate-400 hover:text-slate-600 text-lg font-bold">&times;</button>
            </div>
            <p class="text-xs text-slate-600"><span data-i18n="weigh_desc">Enter truck/trolley verified gross weight for token</span> <span id="weighmentModalToken" class="font-mono font-bold text-emerald-800"></span>.</p>
            <div class="space-y-3 pt-2">
                <div>
                    <label class="text-xs font-semibold text-slate-700" data-i18n="weigh_lbl_weight">Final Verified Weight (Quintals)</label>
                    <input type="number" id="weighmentWeightInput" step="0.1" placeholder="42.5" class="w-full border rounded-lg p-2.5 text-sm font-bold font-mono mt-1">
                    <span class="text-[10px] text-slate-500 mt-1 block" data-i18n="weigh_help">MSP Payout will be instantly re-calculated and locked based on this value.</span>
                </div>
                <button onclick="submitWeighmentWeight()" class="w-full bg-slate-900 hover:bg-black text-white font-bold py-3 rounded-xl text-xs transition shadow" data-i18n="weigh_btn_confirm">
                    Confirm Weight & Proceed to Unloading
                </button>
            </div>
        </div>
    </div>

    <!-- DUAL-ROLE AUTHENTICATION MODAL -->
    <div id="authModal" class="fixed inset-0 bg-slate-900/90 z-[100] flex items-center justify-center hidden">
        <div class="bg-white p-6 md:p-8 rounded-2xl shadow-2xl max-w-md w-full space-y-6">
            
            <div class="flex justify-between items-center pb-3 border-b">
                <h2 class="text-xl font-bold text-slate-800" data-i18n="auth_title">Choose Login Gateway</h2>
                <button onclick="closeAuthModal()" class="text-slate-400 hover:text-slate-600 text-lg font-bold">&times;</button>
            </div>

            <div class="grid grid-cols-2 gap-2 bg-slate-100 p-1.5 rounded-xl text-xs font-bold">
                <button id="tabRoleFarmer" onclick="switchRoleModal('FARMER')" class="py-2 rounded-lg bg-emerald-600 text-white transition shadow" data-i18n="auth_farmer">
                    🌾 Farmer Portal
                </button>
                <button id="tabRoleOfficer" onclick="switchRoleModal('OFFICER')" class="py-2 rounded-lg text-slate-600 hover:text-slate-900 transition" data-i18n="auth_officer">
                    👮 Officer Portal
                </button>
            </div>

            <div id="formFarmer" class="space-y-4">
                <div class="text-center">
                    <p class="text-xs text-slate-500" data-i18n="auth_desc_farmer">Access your slot bookings & DBT transaction status</p>
                </div>
                <div id="farmerStep1" class="space-y-3">
                    <div>
                        <label class="text-xs font-semibold text-slate-600" data-i18n="auth_lbl_name">Farmer Name</label>
                        <input type="text" id="farmerNameInput" placeholder="Enter full name" value="Suresh Kumar Verma" class="w-full border rounded-lg p-3 text-sm mt-1 focus:outline-none focus:ring-2 focus:ring-emerald-500">
                    </div>
                    <div>
                        <label class="text-xs font-semibold text-slate-600" data-i18n="auth_lbl_mobile">Registered Mobile Number (10 Digits)</label>
                        <input type="text" id="farmerMobileInput" maxlength="10" placeholder="9876543210" value="9876543210" class="w-full border rounded-lg p-3 text-sm font-mono mt-1 focus:outline-none focus:ring-2 focus:ring-emerald-500">
                    </div>
                    <button onclick="requestFarmerOTP()" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3 rounded-xl transition shadow-md" data-i18n="auth_btn_otp">
                        Get Verification OTP
                    </button>
                </div>

                <div id="farmerStep2" class="space-y-3 hidden">
                    <div class="bg-emerald-50 p-3 rounded-xl border border-emerald-200 text-xs text-emerald-800">
                        <span data-i18n="auth_otp_sent">OTP sent to your mobile.</span> <span id="otpDebugHint" class="font-bold underline"></span>
                    </div>
                    <div>
                        <label class="text-xs font-semibold text-slate-600" data-i18n="auth_lbl_enter_otp">Enter 6-Digit OTP</label>
                        <input type="text" id="farmerOtpInput" maxlength="6" placeholder="123456" class="w-full border rounded-lg p-3 text-sm font-mono tracking-widest text-center mt-1 focus:outline-none focus:ring-2 focus:ring-emerald-500">
                    </div>
                    <button onclick="verifyAndLoginFarmer()" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3 rounded-xl transition shadow-md" data-i18n="auth_btn_verify">
                        Verify & Enter Portal
                    </button>
                    <button onclick="backToFarmerStep1()" class="w-full text-slate-500 text-xs underline text-center" data-i18n="auth_btn_back">Back to details</button>
                </div>
            </div>

            <div id="formOfficer" class="space-y-4 hidden">
                <div class="text-center">
                    <p class="text-xs text-slate-500" data-i18n="auth_desc_officer">Access gate approvals, queue controls & officer station</p>
                </div>
                <div>
                    <div class="flex justify-between items-center mb-1">
                        <label class="text-xs font-semibold text-slate-600" data-i18n="auth_lbl_pwd">Procurement Officer Password</label>
                        <button type="button" onclick="fillDemoOfficerPwd()" class="text-[11px] text-amber-600 font-bold hover:underline bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                            <i class="fa-solid fa-key mr-1"></i> <span data-i18n="auth_use_demo">Use Demo ID (`admin123`)</span>
                        </button>
                    </div>
                    <input type="password" id="officerPassword" placeholder="Enter Password" class="w-full border rounded-lg p-3 text-sm mt-1 focus:outline-none focus:ring-2 focus:ring-emerald-500">
                </div>
                <button onclick="loginAsOfficer()" class="w-full bg-slate-900 hover:bg-black text-white font-bold py-3 rounded-xl transition shadow-md" data-i18n="auth_btn_officer_login">
                    Authenticate & Enter Gateway
                </button>
            </div>

        </div>
    </div>

    <header class="bg-slate-900 text-white border-b-4 border-amber-500 shadow-md sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 py-2.5 flex flex-wrap justify-between items-center gap-3">
            <div class="flex items-center space-x-3">
                <div class="bg-amber-500 text-slate-900 px-2.5 py-1 rounded-lg font-black text-lg" data-i18n="brand_name">KrishiSetu</div>
                <div>
                    <div class="flex items-center space-x-2">
                        <span class="text-[10px] bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded border border-amber-500/40 font-bold">PS ID: 26032</span>
                        <span class="text-[10px] text-slate-400" data-i18n="doca">Department of Consumer Affairs (DoCA)</span>
                    </div>
                    <h1 class="font-bold text-sm md:text-base leading-tight" data-i18n="app_title">Smart APMC Procurement, Stock Quota & DBT Settlement Hub</h1>
                </div>
            </div>
            
            <div class="flex items-center space-x-3">
                <div class="flex items-center space-x-1.5 bg-slate-800 border border-slate-700 px-2.5 py-1 rounded-lg">
                    <i class="fa-solid fa-language text-amber-400"></i>
                    <select id="langSelect" onchange="changeLanguage(this.value)" class="bg-transparent text-xs font-bold text-white focus:outline-none cursor-pointer">
                        <option value="en" class="bg-slate-900 text-white">English</option>
                        <option value="hi" class="bg-slate-900 text-white">हिन्दी (Hindi)</option>
                        <option value="mr" class="bg-slate-900 text-white">मराठी (Marathi)</option>
                    </select>
                </div>

                <span id="wsStatus" class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-red-900 text-red-200">
                    <span class="w-2 h-2 mr-1.5 bg-red-400 rounded-full animate-pulse"></span> <span data-i18n="status_offline">Offline</span>
                </span>
                
                <button id="btnLoginModalTrigger" onclick="openAuthModal()" class="bg-amber-500 hover:bg-amber-600 text-slate-900 px-3.5 py-1.5 rounded-lg text-xs font-bold transition shadow">
                    <i class="fa-solid fa-right-to-bracket mr-1"></i> <span data-i18n="btn_login_reg">Login / Register</span>
                </button>

                <div id="userBadge" class="hidden flex items-center space-x-2 bg-slate-800 px-3 py-1 rounded-lg border border-slate-700">
                    <span id="userBadgeText" class="text-xs font-bold text-amber-400">User</span>
                    <button onclick="logoutUser()" class="text-red-400 hover:text-red-300 text-xs font-bold ml-2 underline" data-i18n="btn_logout">Logout</button>
                </div>
            </div>
        </div>

        <nav id="mainTabsNav" class="max-w-7xl mx-auto px-4 flex flex-wrap space-x-1 border-t border-slate-800 bg-slate-950/90 text-xs font-medium">
        </nav>
    </header>

    <main class="max-w-7xl mx-auto p-4 space-y-6">

        <section id="marketTab" class="space-y-6">
            <div id="guestLoginNotice" class="bg-gradient-to-r from-amber-500/10 via-emerald-500/10 to-transparent p-4 rounded-2xl border border-amber-500/30 flex flex-wrap justify-between items-center gap-3">
                <div class="flex items-center space-x-3">
                    <div class="p-2.5 bg-amber-500 text-slate-900 rounded-xl text-lg font-black"><i class="fa-solid fa-circle-info"></i></div>
                    <div>
                        <h3 class="font-bold text-slate-800 text-sm" data-i18n="welcome_title">Welcome to KrishiSetu Procurement Hub</h3>
                        <p class="text-xs text-slate-600" data-i18n="welcome_sub">Log in as a Farmer to schedule delivery slots or as a Procurement Officer to manage yard arrivals.</p>
                    </div>
                </div>
                <button onclick="openAuthModal()" class="bg-amber-500 hover:bg-amber-600 text-slate-900 font-bold px-4 py-2 rounded-xl text-xs transition" data-i18n="welcome_btn">
                    Get Started / Login
                </button>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex items-center space-x-3">
                    <div class="p-3 bg-emerald-100 text-emerald-700 rounded-xl text-xl"><i class="fa-solid fa-scale-balanced"></i></div>
                    <div>
                        <span class="text-[11px] text-slate-500 font-bold uppercase block" data-i18n="card_inflow">Today's Total Inflow</span>
                        <span id="marketInflowTotal" class="text-xl font-black text-slate-900">0 Qtl</span>
                    </div>
                </div>

                <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex items-center space-x-3">
                    <div class="p-3 bg-blue-100 text-blue-700 rounded-xl text-xl"><i class="fa-solid fa-users"></i></div>
                    <div>
                        <span class="text-[11px] text-slate-500 font-bold uppercase block" data-i18n="card_farmers">Registered Farmers</span>
                        <span id="marketFarmerTotal" class="text-xl font-black text-slate-900">0</span>
                    </div>
                </div>

                <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex items-center space-x-3">
                    <div class="p-3 bg-amber-100 text-amber-700 rounded-xl text-xl"><i class="fa-solid fa-door-open"></i></div>
                    <div>
                        <span class="text-[11px] text-slate-500 font-bold uppercase block" data-i18n="card_passes">Active Gate Passes</span>
                        <span id="marketActivePasses" class="text-xl font-black text-slate-900">0</span>
                    </div>
                </div>

                <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex items-center space-x-3">
                    <div class="p-3 bg-purple-100 text-purple-700 rounded-xl text-xl"><i class="fa-solid fa-indian-rupee-sign"></i></div>
                    <div>
                        <span class="text-[11px] text-slate-500 font-bold uppercase block" data-i18n="card_dbt">MSP DBT Settlement</span>
                        <span class="text-xl font-black text-purple-700" data-i18n="dbt_direct">100% Direct</span>
                    </div>
                </div>
            </div>

            <div class="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm">
                <div class="flex justify-between items-center mb-4">
                    <div>
                        <h2 class="font-bold text-slate-800 text-base" data-i18n="quotas_title">Mandi Target Quotas vs Current Procured Stock (Required Stock Engine)</h2>
                        <p class="text-xs text-slate-500" data-i18n="quotas_sub">Government procurement targets assigned to this APMC center by DoCA.</p>
                    </div>
                    <span class="text-xs bg-emerald-50 text-emerald-700 font-semibold px-2.5 py-1 rounded border border-emerald-200" data-i18n="badge_live_quotas">Live Quotas</span>
                </div>
                <div id="stockQuotaGrid" class="grid grid-cols-1 md:grid-cols-4 gap-4"></div>
            </div>

            <div class="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm">
                <h3 class="font-bold text-slate-800 text-sm mb-3" data-i18n="msp_rates_title">DoCA Fixed Minimum Support Price (MSP) Rates (2026 Season)</h3>
                <div id="mspRateGrid" class="grid grid-cols-2 md:grid-cols-4 gap-3"></div>
            </div>
        </section>

        <section id="bookingTab" class="hidden grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div class="lg:col-span-4 bg-white rounded-2xl p-5 border border-slate-200 shadow-sm space-y-4">
                <div class="flex items-center space-x-2 pb-3 border-b border-slate-100">
                    <i class="fa-solid fa-id-card text-emerald-600 text-lg"></i>
                    <h2 class="font-bold text-slate-700 text-sm" data-i18n="step1_title">Step 1: Farmer Registration & Stock Owned</h2>
                </div>

                <div class="space-y-3">
                    <div>
                        <label class="text-xs font-semibold text-slate-600" data-i18n="lbl_name">Farmer Name (Aadhaar Verified)</label>
                        <input id="reg_name" type="text" value="Suresh Kumar Verma" class="w-full text-sm border rounded-lg p-2 border-slate-300">
                    </div>
                    <div class="grid grid-cols-2 gap-2">
                        <div>
                            <label class="text-xs font-semibold text-slate-600" data-i18n="lbl_phone">WhatsApp Mobile (10 Digits)</label>
                            <input id="reg_phone" type="text" maxlength="10" value="9876543210" class="w-full text-sm border rounded-lg p-2 border-slate-300 font-mono">
                        </div>
                        <div>
                            <label class="text-xs font-semibold text-slate-600" data-i18n="lbl_aadhaar">Aadhaar (Last 4 Digits)</label>
                            <input id="reg_aadhaar" type="password" maxlength="4" placeholder="1234" class="w-full text-sm border rounded-lg p-2 border-slate-300 font-mono">
                        </div>
                    </div>
                    <div class="grid grid-cols-2 gap-2">
                        <div>
                            <label class="text-xs font-semibold text-slate-600" data-i18n="lbl_bank">Bank Account No.</label>
                            <input id="reg_bank" type="text" value="918273645012" class="w-full text-sm border rounded-lg p-2 border-slate-300 font-mono">
                        </div>
                        <div>
                            <label class="text-xs font-semibold text-slate-600" data-i18n="lbl_ifsc">Bank IFSC (11 Chars)</label>
                            <input id="reg_ifsc" type="text" maxlength="11" value="SBIN0001234" class="w-full text-sm border rounded-lg p-2 border-slate-300 uppercase font-mono">
                        </div>
                    </div>
                    <div class="grid grid-cols-2 gap-2">
                        <div>
                            <label class="text-xs font-semibold text-slate-600" data-i18n="lbl_land">Land Area (Acres)</label>
                            <input id="reg_land" type="number" value="6.5" class="w-full text-sm border rounded-lg p-2 border-slate-300">
                        </div>
                        <div>
                            <label class="text-xs font-semibold text-slate-600" data-i18n="lbl_village">Village / District</label>
                            <input id="reg_village" type="text" value="Hingna, Nagpur" class="w-full text-sm border rounded-lg p-2 border-slate-300">
                        </div>
                    </div>

                    <div>
                        <label class="text-xs font-semibold text-slate-600">Preferred Procurement Center</label>
                        <select id="reg_center" class="w-full text-sm border rounded-lg p-2 border-slate-300 font-bold text-slate-700 bg-white mt-1">
                            <option value="Nagpur Central APMC Yard 01">Nagpur Central APMC Yard 01</option>
                            <option value="Hingna Sub-Yard 02">Hingna Sub-Yard 02</option>
                            <option value="Butibori Agro Hub 03">Butibori Agro Hub 03</option>
                        </select>
                    </div>
                    
                    <div class="bg-amber-50 p-3 rounded-xl border border-amber-200">
                        <label class="text-xs font-bold text-amber-900" data-i18n="lbl_total_stock">Total Harvest Stock Farmer Has at Home (Qtl)</label>
                        <input id="reg_total_stock" type="number" value="120" class="w-full text-sm border rounded-lg p-2 border-amber-300 bg-white font-bold text-amber-900 mt-1">
                        <span class="text-[10px] text-amber-700 block mt-1" data-i18n="stock_help">Anti-hoarding verification: Limits slot booking to genuine harvest yields.</span>
                    </div>

                    <button onclick="registerFarmer()" class="w-full bg-slate-900 hover:bg-black text-white font-semibold py-2.5 rounded-lg text-xs transition">
                        <i class="fa-solid fa-floppy-disk mr-1"></i> <span data-i18n="btn_register">Register & Link Bank A/C</span>
                    </button>
                    <p id="regStatus" class="text-[11px] text-center text-emerald-700 font-medium"></p>
                </div>
            </div>

            <div class="lg:col-span-8 bg-white rounded-2xl p-5 border border-slate-200 shadow-sm space-y-4">
                <div class="flex items-center space-x-2 pb-3 border-b border-slate-100">
                    <i class="fa-solid fa-calendar-check text-emerald-600 text-lg"></i>
                    <h2 class="font-bold text-slate-700 text-sm" data-i18n="step2_title">Step 2: Schedule Delivery & Send to Procurement Officer</h2>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div class="space-y-3">
                        <div>
                            <label class="text-xs font-semibold text-slate-600" data-i18n="lbl_reg_phone">Registered Phone No. (10 Digits)</label>
                            <input id="book_phone" type="text" maxlength="10" value="9876543210" class="w-full text-sm border rounded-lg p-2 border-slate-300 font-mono">
                        </div>
                        <div class="grid grid-cols-2 gap-2">
                            <div>
                                <label class="text-xs font-semibold text-slate-600" data-i18n="lbl_commodity">Commodity</label>
                                <select id="book_crop" onchange="calcMSP()" class="w-full text-sm border rounded-lg p-2 border-slate-300 font-bold text-emerald-800">
                                    <option value="Soybean">Soybean</option>
                                    <option value="Wheat">Wheat</option>
                                    <option value="Paddy (Rice)">Paddy (Rice)</option>
                                    <option value="Cotton">Cotton</option>
                                </select>
                            </div>
                            <div>
                                <label class="text-xs font-semibold text-slate-600" data-i18n="lbl_brought_qtl">Quantity Brought (Qtl)</label>
                                <input id="book_weight" oninput="calcMSP()" type="number" value="40" class="w-full text-sm border rounded-lg p-2 border-slate-300 font-bold">
                            </div>
                        </div>

                        <div class="grid grid-cols-2 gap-2">
                            <div>
                                <label class="text-xs font-semibold text-slate-600" data-i18n="lbl_vehicle_type">Vehicle Type</label>
                                <select id="book_vehicle_type" class="w-full text-sm border rounded-lg p-2 border-slate-300">
                                    <option>Tractor Trolley</option>
                                    <option>Mini Truck</option>
                                    <option>Bullock Cart</option>
                                </select>
                            </div>
                            <div>
                                <label class="text-xs font-semibold text-slate-600" data-i18n="lbl_vehicle_no">Vehicle Plate No.</label>
                                <input id="book_vehicle_no" type="text" value="MH-31-TR-9044" class="w-full text-sm border rounded-lg p-2 border-slate-300 font-mono uppercase">
                            </div>
                        </div>

                        <div>
                            <label class="text-xs font-semibold text-slate-600" data-i18n="lbl_slot_window">Target Time Window (Live Slots)</label>
                            <select id="book_slot" class="w-full text-sm border rounded-lg p-2 border-slate-300 font-bold text-slate-700 bg-slate-50">
                                <option value="">Loading slots...</option>
                            </select>
                        </div>

                        <div class="bg-emerald-50 p-3 rounded-xl border border-emerald-200 flex justify-between items-center">
                            <div>
                                <span class="text-[10px] text-emerald-800 uppercase font-bold block" data-i18n="lbl_est_msp">Estimated MSP Total Value</span>
                                <span id="estMSPText" class="text-lg font-black text-emerald-700">₹1,95,680.00</span>
                            </div>
                            <span class="text-xs bg-emerald-200 text-emerald-900 px-2 py-1 rounded font-semibold" data-i18n="badge_dbt_assured">100% DBT Assured</span>
                        </div>

                        <button onclick="bookSlot()" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3 rounded-xl shadow-lg transition flex items-center justify-center space-x-2">
                            <i class="fa-solid fa-paper-plane"></i>
                            <span data-i18n="btn_send_request">Send Booking Request to Procurement Officer</span>
                        </button>
                    </div>

                    <div class="border border-slate-200 rounded-xl p-4 bg-slate-50 flex flex-col justify-between">
                        <div id="passEmpty" class="text-center py-12 text-slate-400 text-xs">
                            <i class="fa-solid fa-ticket text-4xl mb-2 block"></i>
                            <span data-i18n="pass_empty">No pass generated yet.<br>Complete booking to view pass status.</span>
                        </div>

                        <div id="passReady" class="hidden space-y-3">
                            <div class="flex justify-between items-start">
                                <div>
                                    <span id="passStatusBadge" class="text-[10px] bg-amber-500 text-slate-900 px-2 py-0.5 rounded font-bold uppercase">Awaiting Approval</span>
                                    <h3 id="cardTokenId" class="text-base font-black text-slate-900 font-mono mt-1">TKN-XXX</h3>
                                    <p id="cardFarmer" class="text-xs text-slate-600 font-medium">Farmer Name</p>
                                </div>
                                <div id="cardQRCode" class="bg-white p-1 rounded border border-slate-200 shadow-sm"></div>
                            </div>

                            <div class="bg-white p-3 rounded-lg border border-slate-200 text-xs space-y-1">
                                <div class="flex justify-between">
                                    <span class="text-slate-500" data-i18n="pass_slot">Allotted Slot:</span>
                                    <span id="cardSlot" class="font-bold text-slate-800">08:00 - 10:00</span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-slate-500" data-i18n="pass_officer_status">Procurement Officer Status:</span>
                                    <span id="cardOfficerStatus" class="font-bold text-amber-700">PENDING_APPROVAL</span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-slate-500" data-i18n="pass_live_stage">Live Stage:</span>
                                    <span id="cardStage" class="font-bold text-emerald-700">REQUESTED</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <section id="officerTab" class="hidden space-y-6">
            <div class="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm">
                <div class="flex justify-between items-center pb-4 border-b border-slate-100">
                    <div class="flex items-center space-x-3">
                        <div class="p-2.5 bg-amber-500 text-slate-900 rounded-xl text-lg font-black"><i class="fa-solid fa-stamp"></i></div>
                        <div>
                            <h2 class="font-bold text-slate-800 text-base" data-i18n="officer_title">Procurement Officer Approval Station</h2>
                            <p class="text-xs text-slate-500" data-i18n="officer_sub">Review incoming farmer delivery requests, verify stock declarations, and grant entry passes.</p>
                        </div>
                    </div>
                </div>

                <div class="overflow-x-auto mt-4">
                    <table class="w-full text-left text-xs">
                        <thead class="bg-slate-50 text-slate-500 uppercase sticky top-0">
                            <tr>
                                <th class="p-3" data-i18n="th_token">Token</th>
                                <th class="p-3" data-i18n="th_farmer">Farmer & Encrypted Contact</th>
                                <th class="p-3" data-i18n="th_stock">Stock Declared (Farm vs Brought)</th>
                                <th class="p-3" data-i18n="th_req_slot">Requested Slot</th>
                                <th class="p-3" data-i18n="th_decision">Officer Decision Status</th>
                                <th class="p-3 text-right" data-i18n="th_action">Action</th>
                            </tr>
                        </thead>
                        <tbody id="officerTableBody" class="divide-y divide-slate-100">
                            <tr>
                                <td colspan="6" class="text-center p-8 text-slate-400" data-i18n="officer_empty">No incoming farmer requests awaiting approval.</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

        <section id="registryTab" class="hidden space-y-6">
            <div class="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm">
                <div class="flex justify-between items-center pb-4 border-b border-slate-100">
                    <div class="flex items-center space-x-3">
                        <div class="p-2.5 bg-blue-500 text-white rounded-xl text-lg font-black"><i class="fa-solid fa-list"></i></div>
                        <div>
                            <h2 class="font-bold text-slate-800 text-base" data-i18n="reg_tab_title">Registered Farmers by Slot</h2>
                            <p class="text-xs text-slate-500" data-i18n="reg_tab_sub">Overview of all farmer bookings categorized by their allocated time slots.</p>
                        </div>
                    </div>
                    <button onclick="downloadOfficerFile('registry')" class="bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold px-4 py-2 rounded-lg shadow-sm transition flex items-center space-x-2">
                        <i class="fa-solid fa-shield-halved"></i><span data-i18n="btn_dl_registry">Download Secure Registry</span>
                    </button>
                </div>
                <div id="slotRegistryContent" class="mt-4 space-y-6">
                </div>
            </div>
        </section>

        <section id="queueTab" class="hidden space-y-6">
            <div class="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm">
                <div class="flex justify-between items-center mb-3">
                    <h3 class="text-xs font-bold text-slate-500 uppercase tracking-wider" data-i18n="cap_header">Mandi Weighbridge Capacity per Slot (Max 120 Qtl/Window)</h3>
                    <span class="text-xs text-emerald-700 font-semibold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200" data-i18n="badge_throttling">Dynamic Inflow Throttling Active</span>
                </div>
                <div id="capacityBars" class="grid grid-cols-2 md:grid-cols-4 gap-4"></div>
            </div>

            <div class="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm">
                <div class="flex justify-between items-center mb-4">
                    <div class="flex items-center space-x-2">
                        <i class="fa-solid fa-sliders text-emerald-600"></i>
                        <h2 class="font-bold text-slate-800 text-sm" data-i18n="queue_title">Gate & Yard Stage Machine Controller</h2>
                    </div>
                    <span id="activeLoadsBadge" class="text-xs bg-slate-900 text-white font-semibold px-3 py-1 rounded-full">0 Active Vehicles</span>
                </div>

                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs">
                        <thead class="bg-slate-50 text-slate-500 uppercase">
                            <tr>
                                <th class="p-3" data-i18n="th_token">Token</th>
                                <th class="p-3" data-i18n="th_farmer_veh">Farmer & Vehicle</th>
                                <th class="p-3" data-i18n="th_crop_wt">Crop & Weight</th>
                                <th class="p-3" data-i18n="th_stage">Yard Stage</th>
                                <th class="p-3 text-right" data-i18n="th_yard_action">Yard Action</th>
                            </tr>
                        </thead>
                        <tbody id="mandiTableBody" class="divide-y divide-slate-100">
                            <tr>
                                <td colspan="5" class="text-center p-8 text-slate-400" data-i18n="yard_clear">Yard is currently clear.</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="bg-amber-50 rounded-2xl border border-amber-200 p-5">
                <div class="flex items-center space-x-2 mb-2">
                    <i class="fa-solid fa-triangle-exclamation text-amber-700 text-lg"></i>
                    <h3 class="font-bold text-amber-900 text-sm" data-i18n="emg_title">Emergency Yard Delay Trigger</h3>
                </div>
                <div class="flex flex-wrap gap-3">
                    <button onclick="triggerEmergency(30, 'Weighbridge Maintenance Glitch')" class="bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold px-4 py-2 rounded-lg">
                        <i class="fa-solid fa-clock mr-1"></i> <span data-i18n="btn_delay_30">Apply +30 Mins Delay</span>
                    </button>
                    <button onclick="triggerEmergency(60, 'Heavy Rainfall / Waterlogging')" class="bg-amber-800 hover:bg-amber-900 text-white text-xs font-bold px-4 py-2 rounded-lg">
                        <i class="fa-solid fa-cloud-showers-heavy mr-1"></i> <span data-i18n="btn_delay_60">Apply +60 Mins Delay</span>
                    </button>
                </div>
            </div>
        </section>

        <section id="trackerTab" class="hidden space-y-6">
            <div class="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm">
                <div class="flex justify-between items-center pb-4 border-b border-slate-100">
                    <div>
                        <h2 class="font-bold text-slate-800 text-base" data-i18n="dbt_title">Direct Benefit Transfer (DBT) Payout Ledger</h2>
                        <p class="text-xs text-slate-500" data-i18n="dbt_sub">Live payment verification from unloading to farmer bank account credit.</p>
                    </div>
                    <button id="officerLedgerDownload" onclick="downloadOfficerFile('ledger')" class="hidden bg-slate-900 hover:bg-black text-white text-xs font-bold px-4 py-2 rounded-lg shadow-sm transition flex items-center space-x-2">
                        <i class="fa-solid fa-shield-halved"></i><span data-i18n="btn_dl_ledger">Download Secure Ledger</span>
                    </button>
                </div>
                <div class="overflow-x-auto mt-4">
                    <table class="w-full text-left text-xs">
                        <thead class="bg-slate-50 text-slate-500 uppercase sticky top-0">
                            <tr>
                                <th class="p-3" data-i18n="th_token_time">Token & Time</th>
                                <th class="p-3" data-i18n="th_farmer_acc">Farmer & Secure A/C</th>
                                <th class="p-3" data-i18n="th_comm_wt">Commodity & Weight</th>
                                <th class="p-3" data-i18n="th_stage">Yard Stage</th>
                                <th class="p-3" data-i18n="th_calc_msp">Calculated MSP Payout</th>
                                <th class="p-3" data-i18n="th_dbt_status">DBT Settlement Status</th>
                                <th class="p-3 text-right" id="th_receipt_action" data-i18n="th_action">Action</th>
                            </tr>
                        </thead>
                        <tbody id="paymentLedgerBody" class="divide-y divide-slate-100">
                            <tr>
                                <td colspan="7" class="text-center p-8 text-slate-400" data-i18n="dbt_empty">No transactions recorded yet.</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

    </main>

    <script>
        let currentPassToken = null;
        let qrCodeInstance = null;
        let currentLang = 'en';
        let latestStateData = null;
        let currentActiveTab = 'marketTab';
        
        let currentUserRole = null; 
        let currentFarmerPhone = null;
        let currentFarmerName = null;
        let officerToken = null;
        let activeModalTokenId = null;

        const translations = {
            en: {
                brand_name: "KrishiSetu",
                crops: { "Soybean": "Soybean", "Wheat": "Wheat", "Paddy (Rice)": "Paddy (Rice)", "Cotton": "Cotton" },
                doca: "Department of Consumer Affairs (DoCA)",
                app_title: "Smart APMC Procurement, Stock Quota & DBT Settlement Hub",
                status_offline: "Offline",
                status_live: "Live System Sync",
                tab_market: "Live Market Status & Quotas",
                tab_booking: "Farmer Stock & Slot Booking",
                tab_officer: "Procurement Officer Gateway",
                tab_registry: "Slot Registry",
                tab_queue: "Live Queue & Gate Dispatch",
                tab_tracker: "DBT Payment Ledger",
                card_inflow: "Today's Total Inflow",
                card_farmers: "Registered Farmers",
                card_passes: "Active Gate Passes",
                card_dbt: "MSP DBT Settlement",
                dbt_direct: "100% Direct",
                quotas_title: "Mandi Target Quotas vs Current Procured Stock (Required Stock Engine)",
                quotas_sub: "Government procurement targets assigned to this APMC center by DoCA.",
                badge_live_quotas: "Live Quotas",
                msp_rates_title: "DoCA Fixed Minimum Support Price (MSP) Rates (2026 Season)",
                step1_title: "Step 1: Farmer Registration & Stock Owned",
                lbl_name: "Farmer Name (Aadhaar Verified)",
                lbl_phone: "WhatsApp Mobile (10 Digits)",
                lbl_aadhaar: "Aadhaar (Last 4 Digits)",
                lbl_aadhaar_ph: "1234",
                lbl_bank: "Bank Account No.",
                lbl_ifsc: "Bank IFSC (11 Chars)",
                lbl_land: "Land Area (Acres)",
                lbl_village: "Village / District",
                lbl_total_stock: "Total Harvest Stock Farmer Has at Home (Qtl)",
                stock_help: "Anti-hoarding verification: Limits slot booking to genuine harvest yields.",
                btn_register: "Register & Link Bank A/C",
                step2_title: "Step 2: Schedule Delivery & Send to Procurement Officer",
                lbl_reg_phone: "Registered Phone No. (10 Digits)",
                lbl_commodity: "Commodity",
                lbl_brought_qtl: "Quantity Brought (Qtl)",
                lbl_vehicle_type: "Vehicle Type",
                lbl_vehicle_no: "Vehicle Plate No.",
                lbl_slot_window: "Target Time Window (Live Slots)",
                lbl_est_msp: "Estimated MSP Total Value",
                badge_dbt_assured: "100% DBT Assured",
                btn_send_request: "Send Booking Request to Procurement Officer",
                pass_empty: "No pass generated yet.<br>Complete booking to view pass status.",
                pass_slot: "Allotted Slot:",
                pass_officer_status: "Procurement Officer Status:",
                pass_live_stage: "Live Stage:",
                officer_title: "Procurement Officer Approval Station",
                officer_sub: "Review incoming farmer delivery requests, verify stock declarations, and grant entry passes.",
                th_token: "Token",
                th_farmer: "Farmer & Encrypted Contact",
                th_stock: "Stock Declared (Farm vs Brought)",
                th_req_slot: "Requested Slot",
                th_decision: "Officer Decision Status",
                th_action: "Action",
                officer_empty: "No incoming farmer requests awaiting approval.",
                cap_header: "Mandi Weighbridge Capacity per Slot (Max 120 Qtl/Window)",
                badge_throttling: "Dynamic Inflow Throttling Active",
                queue_title: "Gate & Yard Stage Machine Controller",
                th_farmer_veh: "Farmer & Vehicle",
                th_crop_wt: "Crop & Weight",
                th_stage: "Yard Stage",
                th_yard_action: "Yard Action",
                yard_clear: "Yard is currently clear.",
                emg_title: "Emergency Yard Delay Trigger",
                btn_delay_30: "Apply +30 Mins Delay",
                btn_delay_60: "Apply +60 Mins Delay",
                dbt_title: "Direct Benefit Transfer (DBT) Payout Ledger",
                dbt_sub: "Live payment verification from unloading to farmer bank account credit.",
                th_token_time: "Token & Time",
                th_farmer_acc: "Farmer & Secure A/C",
                th_comm_wt: "Commodity & Weight",
                th_calc_msp: "Calculated MSP Payout",
                th_dbt_status: "DBT Settlement Status",
                dbt_empty: "No transactions recorded yet.",
                auth_title: "Choose Login Gateway",
                auth_farmer: "🌾 Farmer Portal",
                auth_officer: "👮 Officer Portal",
                auth_desc_farmer: "Access your slot bookings & DBT transaction status",
                auth_lbl_name: "Farmer Name",
                auth_lbl_mobile: "Registered Mobile Number (10 Digits)",
                auth_btn_otp: "Get Verification OTP",
                auth_otp_sent: "OTP sent to your mobile.",
                auth_lbl_enter_otp: "Enter 6-Digit OTP",
                auth_btn_verify: "Verify & Enter Portal",
                auth_btn_back: "Back to details",
                auth_desc_officer: "Access gate approvals, queue controls & officer station",
                auth_lbl_pwd: "Procurement Officer Password",
                auth_use_demo: "Use Demo ID (`admin123`)",
                auth_btn_officer_login: "Authenticate & Enter Gateway",
                btn_login_reg: "Login / Register",
                btn_logout: "Logout",
                welcome_title: "Welcome to KrishiSetu Procurement Hub",
                welcome_sub: "Log in as a Farmer to schedule delivery slots or as a Procurement Officer to manage yard arrivals.",
                welcome_btn: "Get Started / Login",
                btn_dl_registry: "Download Secure Registry",
                btn_dl_ledger: "Download Secure Ledger",
                reg_tab_title: "Registered Farmers by Slot",
                reg_tab_sub: "Overview of all farmer bookings categorized by their allocated time slots.",
                assay_title: "Assaying Quality Inspection",
                assay_desc: "Inspect moisture, purity, and grain standards for token",
                assay_lbl_remarks: "Inspection Result / Remarks",
                assay_btn_good: "Good (Pass & Forward)",
                assay_btn_bad: "Bad (Reject Stock)",
                weigh_title: "Weighbridge Final Measurement",
                weigh_desc: "Enter truck/trolley verified gross weight for token",
                weigh_lbl_weight: "Final Verified Weight (Quintals)",
                weigh_help: "MSP Payout will be instantly re-calculated and locked based on this value.",
                weigh_btn_confirm: "Confirm Weight & Proceed to Unloading"
            },
            hi: {
                brand_name: "कृषिसेतू",
                crops: { "Soybean": "सोयाबीन", "Wheat": "गेहूँ", "Paddy (Rice)": "धान (चावल)", "Cotton": "कपास" },
                doca: "उपभोक्ता मामले विभाग (DoCA)",
                app_title: "स्मार्ट APMC खरीद, स्टॉक कोटा और DBT निपटान हब",
                status_offline: "ऑफ़लाइन",
                status_live: "लाइव सिस्टम सिंक",
                tab_market: "लाइव मार्केट स्थिति और कोटा",
                tab_booking: "किसान स्टॉक और स्लॉट बुकिंग",
                tab_officer: "खरीद अधिकारी गेटवे",
                tab_registry: "स्लॉट रजिस्ट्री",
                tab_queue: "लाइव कतार और गेट प्रेषण",
                tab_tracker: "DBT भुगतान लेजर",
                card_inflow: "आज की कुल आवक",
                card_farmers: "पंजीकृत किसान",
                card_passes: "सक्रिय गेट पास",
                card_dbt: "MSP DBT निपटान",
                dbt_direct: "100% प्रत्यक्ष",
                quotas_title: "मंडी लक्ष्य कोटा बनाम वर्तमान खरीद स्टॉक (आवश्यक स्टॉक इंजन)",
                quotas_sub: "DoCA द्वारा इस APMC केंद्र को सौंपे गए सरकारी खरीद लक्ष्य।",
                badge_live_quotas: "लाइव कोटा",
                msp_rates_title: "DoCA निर्धारित न्यूनतम समर्थन मूल्य (MSP) दरें (2026 सीज़न)",
                step1_title: "चरण 1: किसान पंजीकरण और स्वामित्व वाला स्टॉक",
                lbl_name: "किसान का नाम (आधार सत्यापित)",
                lbl_phone: "व्हाट्सएप मोबाइल (10 अंक)",
                lbl_aadhaar: "आधार (अंतिम 4 अंक)",
                lbl_aadhaar_ph: "1234",
                lbl_bank: "बैंक खाता संख्या",
                lbl_ifsc: "बैंक IFSC (11 अक्षर)",
                lbl_land: "भूमि क्षेत्र (एकड़)",
                lbl_village: "गांव / जिला",
                lbl_total_stock: "किसान के पास घर पर कुल फसल स्टॉक (क्विंटल)",
                stock_help: "जमाखोरी विरोधी सत्यापन: स्लॉट बुकिंग को वास्तविक फसल उपज तक सीमित करता है।",
                btn_register: "पंजीकरण करें और बैंक खाता लिंक करें",
                step2_title: "चरण 2: डिलीवरी शेड्यूल करें और खरीद अधिकारी को भेजें",
                lbl_reg_phone: "पंजीकृत फोन नंबर (10 अंक)",
                lbl_commodity: "जिंस (Commodity)",
                lbl_brought_qtl: "लाई गई मात्रा (क्विंटल)",
                lbl_vehicle_type: "वाहन का प्रकार",
                lbl_vehicle_no: "वाहन प्लेट नंबर",
                lbl_slot_window: "लक्ष्य समय विंडो (लाइव स्लॉट)",
                lbl_est_msp: "अनुमानित MSP कुल मूल्य",
                badge_dbt_assured: "100% DBT सुनिश्चित",
                btn_send_request: "खरीद अधिकारी को बुकिंग अनुरोध भेजें",
                pass_empty: "अभी तक कोई पास नहीं बना है।<br>पास की स्थिति देखने के लिए बुकिंग पूरी करें।",
                pass_slot: "आवंटित स्लॉट:",
                pass_officer_status: "खरीद अधिकारी की स्थिति:",
                pass_live_stage: "लाइव चरण:",
                officer_title: "खरीद अधिकारी अनुमोदन स्टेशन",
                officer_sub: "आने वाले किसान वितरण अनुरोधों की समीक्षा करें, स्टॉक घोषणाओं को सत्यापित करें, और प्रवेश पास प्रदान करें।",
                th_token: "टोकन",
                th_farmer: "किसान और एन्क्रिप्टेड संपर्क",
                th_stock: "घोषित स्टॉक (खेत बनाम लाया गया)",
                th_req_slot: "अनुरोधित स्लॉट",
                th_decision: "अधिकारी निर्णय की स्थिति",
                th_action: "कार्रवाई",
                officer_empty: "अनुमोदन की प्रतीक्षा में कोई आने वाला किसान अनुरोध नहीं है।",
                cap_header: "मंडी वेयब्रिज क्षमता प्रति स्लॉट (अधिकतम 120 क्विंटल/विंडो)",
                badge_throttling: "डायनेमिक इन्फ्लो थ्रॉटलिंग सक्रिय",
                queue_title: "गेट और यार्ड स्टेज मशीन कंट्रोलर",
                th_farmer_veh: "किसान और वाहन",
                th_crop_wt: "फसल और वजन",
                th_stage: "यार्ड चरण",
                th_yard_action: "यार्ड कार्रवाई",
                yard_clear: "यार्ड वर्तमान में खाली है।",
                emg_title: "आपातकालीन यार्ड विलंब ट्रिगर",
                btn_delay_30: "+30 मिनट विलंब लागू करें",
                btn_delay_60: "+60 मिनट विलंब लागू करें",
                dbt_title: "प्रत्यक्ष लाभ अंतरण (DBT) भुगतान लेजर",
                dbt_sub: "अनलोडिंग से लेकर किसान के बैंक खाते में क्रेडिट होने तक लाइव भुगतान सत्यापन।",
                th_token_time: "टोकन और समय",
                th_farmer_acc: "किसान और सुरक्षित खाता",
                th_comm_wt: "जिंस और वजन",
                th_calc_msp: "गणित MSP भुगतान",
                th_dbt_status: "DBT निपटान स्थिति",
                dbt_empty: "अभी तक कोई लेनदेन दर्ज नहीं किया गया है।",
                auth_title: "लॉगिन गेटवे चुनें",
                auth_farmer: "🌾 किसान पोर्टल",
                auth_officer: "👮 अधिकारी पोर्टल",
                auth_desc_farmer: "अपनी स्लॉट बुकिंग और DBT लेनदेन की स्थिति तक पहुंचें",
                auth_lbl_name: "किसान का नाम",
                auth_lbl_mobile: "पंजीकृत मोबाइल नंबर (10 अंक)",
                auth_btn_otp: "सत्यापन OTP प्राप्त करें",
                auth_otp_sent: "आपके मोबाइल पर OTP भेज दिया गया है।",
                auth_lbl_enter_otp: "6-अंकों का OTP दर्ज करें",
                auth_btn_verify: "सत्यापित करें और पोर्टल में प्रवेश करें",
                auth_btn_back: "विवरण पर वापस जाएं",
                auth_desc_officer: "गेट अनुमोदन, कतार नियंत्रण और अधिकारी स्टेशन तक पहुंचें",
                auth_lbl_pwd: "खरीद अधिकारी पासवर्ड",
                auth_use_demo: "डेमो आईडी उपयोग करें (`admin123`)",
                auth_btn_officer_login: "प्रमाणित करें और गेटवे में प्रवेश करें",
                btn_login_reg: "लॉगिन / रजिस्टर",
                btn_logout: "लॉगआउट",
                welcome_title: "कृषिसेतू खरीद हब में आपका स्वागत है",
                welcome_sub: "डिलीवरी स्लॉट शेड्यूल करने के लिए किसान के रूप में या यार्ड आगमन का प्रबंधन करने के लिए खरीद अधिकारी के रूप में लॉग इन करें।",
                welcome_btn: "प्रारंभ करें / लॉगिन",
                btn_dl_registry: "सुरक्षित रजिस्ट्री डाउनलोड करें",
                btn_dl_ledger: "सुरक्षित लेजर डाउनलोड करें",
                reg_tab_title: "स्लॉट के अनुसार पंजीकृत किसान",
                reg_tab_sub: "उनके आवंटित समय स्लॉट द्वारा वर्गीकृत सभी किसान बुकिंग का अवलोकन।",
                assay_title: "एस्सेइंग गुणवत्ता निरीक्षण",
                assay_desc: "टोकन के लिए नमी, शुद्धता और अनाज के मानकों का निरीक्षण करें",
                assay_lbl_remarks: "निरीक्षण परिणाम / टिप्पणी",
                assay_btn_good: "अच्छा (पास और आगे भेजें)",
                assay_btn_bad: "खराब (स्टॉक अस्वीकार करें)",
                weigh_title: "वेयब्रिज अंतिम माप",
                weigh_desc: "टोकन के लिए ट्रक/ट्रॉली सत्यापित सकल वजन दर्ज करें",
                weigh_lbl_weight: "अंतिम सत्यापित वजन (क्विंटल)",
                weigh_help: "MSP भुगतान इस मान के आधार पर तुरंत पुनर्गणना और लॉक किया जाएगा।",
                weigh_btn_confirm: "वजन की पुष्टि करें और अनलोडिंग के लिए आगे बढ़ें"
            },
            mr: {
                brand_name: "कृषीसेतू",
                crops: { "Soybean": "सोयाबीन", "Wheat": "गहू", "Paddy (Rice)": "धान (तांदूळ)", "Cotton": "कापूस" },
                doca: "ग्राहक व्यवहार विभाग (DoCA)",
                app_title: "स्मार्ट APMC खरेदी, स्टॉक कोटा आणि DBT सेटलमेंट हब",
                status_offline: "ऑफलाइन",
                status_live: "थेट प्रणाली सिंक",
                tab_market: "थेट बाजार स्थिती आणि कोटा",
                tab_booking: "शेतकरी स्टॉक आणि स्लॉट बुकिंग",
                tab_officer: "खरेदी अधिकारी गेटवे",
                tab_registry: "स्लॉट नोंदणी",
                tab_queue: "थेट रांग आणि गेट पाठवणे",
                tab_tracker: "DBT पेमेंट खातेवही",
                card_inflow: "आजची एकूण आवक",
                card_farmers: "नोंदणीकृत शेतकरी",
                card_passes: "सक्रिय गेट पास",
                card_dbt: "MSP DBT सेटलमेंट",
                dbt_direct: "100% थेट",
                quotas_title: "मंडी लक्ष्य कोटा वि वर्तमान खरेदी स्टॉक (आवश्यक स्टॉक इंजिन)",
                quotas_sub: "DoCA द्वारे या APMC केंद्राला दिलेले सरकारी खरेदी उद्दिष्ट्ये.",
                badge_live_quotas: "थेट कोटा",
                msp_rates_title: "DoCA निश्चित किमान आधारभूत किंमत (MSP) दर (२०२६ हंगाम)",
                step1_title: "पायरी १: शेतकरी नोंदणी आणि स्वतःचा स्टॉक",
                lbl_name: "शेतकऱ्याचे नाव (आधार सत्यापित)",
                lbl_phone: "व्हॉट्सॲप मोबाईल (१० अंक)",
                lbl_aadhaar: "आधार (शेवटचे ४ अंक)",
                lbl_aadhaar_ph: "1234",
                lbl_bank: "बँक खाते क्रमांक",
                lbl_ifsc: "बँक IFSC (११ अक्षरे)",
                lbl_land: "जमीन क्षेत्र (एकर)",
                lbl_village: "गाव / जिल्हा",
                lbl_total_stock: "शेतकऱ्याकडे घरी असलेला एकूण पीक साठा (क्विंटल)",
                stock_help: "साठेबाजी विरोधी पडताळणी: स्लॉट बुकिंगला खऱ्या पीक उत्पन्नापुरते मर्यादित करते.",
                btn_register: "नोंदणी करा आणि बँक खाते लिंक करा",
                step2_title: "पायरी २: डिलिव्हरी शेड्यूल करा आणि खरेदी अधिकाऱ्याला पाठवा",
                lbl_reg_phone: "नोंदणीकृत फोन क्रमांक (१० अंक)",
                lbl_commodity: "शेतमाल",
                lbl_brought_qtl: "आणलेले प्रमाण (क्विंटल)",
                lbl_vehicle_type: "वाहनाचा प्रकार",
                lbl_vehicle_no: "वाहन प्लेट क्रमांक",
                lbl_slot_window: "लक्ष्य वेळ विंडो (थेट स्लॉट)",
                lbl_est_msp: "अंदाजित MSP एकूण मूल्य",
                badge_dbt_assured: "१००% DBT निश्चित",
                btn_send_request: "खरेदी अधिकाऱ्याला बुकिंग विनंती पाठवा",
                pass_empty: "अद्याप कोणताही पास तयार झालेला नाही.<br>पासची स्थिती पाहण्यासाठी बुकिंग पूर्ण करा.",
                pass_slot: "वाटप केलेला स्लॉट:",
                pass_officer_status: "खरेदी अधिकाऱ्याची स्थिती:",
                pass_live_stage: "थेट टप्पा:",
                officer_title: "खरेदी अधिकारी मंजुरी केंद्र",
                officer_sub: "येणाऱ्या शेतकरी डिलिव्हरी विनंत्यांचे पुनरावलोकन करा, स्टॉक घोषणांची पडताळणी करा आणि प्रवेश पास द्या.",
                th_token: "टोकन",
                th_farmer: "शेतकरी आणि कूटबद्ध संपर्क",
                th_stock: "जाहीर केलेला स्टॉक (शेत वि आणलेला)",
                th_req_slot: "विनंती केलेला स्लॉट",
                th_decision: "अधिकारी निर्णयाची स्थिती",
                th_action: "कृती",
                officer_empty: "मंजुरीच्या प्रतीक्षेत कोणतीही शेतकरी विनंती नाही.",
                cap_header: "मंडी वजनकाटा क्षमता प्रति स्लॉट (कमाल १२० क्विंटल/विंडो)",
                badge_throttling: "डायनॅमिक इनफ्लो थ्रॉटलिंग सक्रिय",
                queue_title: "गेट आणि यार्ड स्टेज मशीन कंट्रोलर",
                th_farmer_veh: "शेतकरी आणि वाहन",
                th_crop_wt: "पीक आणि वजन",
                th_stage: "यार्ड टप्पा",
                th_yard_action: "यार्ड कृती",
                yard_clear: "यार्ड सध्या रिकामे आहे.",
                emg_title: "आणीबाणी यार्ड विलंब ट्रिगर",
                btn_delay_30: "+३० मिनिटे विलंब लागू करा",
                btn_delay_60: "+६० मिनिटे विलंब लागू करा",
                dbt_title: "थेट लाभ हस्तांतरण (DBT) पेमेंट खातेवही",
                dbt_sub: "अनलोडिंगपासून ते शेतकऱ्याच्या बँक खात्यात जमा होईपर्यंत थेट पेमेंट पडताळणी.",
                th_token_time: "टोकन आणि वेळ",
                th_farmer_acc: "शेतकरी आणि सुरक्षित खाते",
                th_comm_wt: "शेतमाल आणि वजन",
                th_calc_msp: "मोजलेले MSP पेमेंट",
                th_dbt_status: "DBT सेटलमेंट स्थिती",
                dbt_empty: "अद्याप कोणताही व्यवहार नोंदवलेला नाही.",
                auth_title: "लॉगिन गेटवे निवडा",
                auth_farmer: "🌾 शेतकरी पोर्टल",
                auth_officer: "👮 अधिकारी पोर्टल",
                auth_desc_farmer: "तुमचे स्लॉट बुकिंग आणि DBT व्यवहार स्थिती तपासा",
                auth_lbl_name: "शेतकऱ्याचे नाव",
                auth_lbl_mobile: "नोंदणीकृत मोबाईल क्रमांक (१० अंक)",
                auth_btn_otp: "पडताळणी OTP मिळवा",
                auth_otp_sent: "तुमच्या मोबाईलवर OTP पाठवला आहे.",
                auth_lbl_enter_otp: "६-अंकी OTP प्रविष्ट करा",
                auth_btn_verify: "प्रमाणित करा आणि पोर्टलमध्ये प्रवेश करा",
                auth_btn_back: "तपशीलांवर परत जा",
                auth_desc_officer: "गेट मंजुरी, रांग नियंत्रण आणि अधिकारी स्टेशनवर प्रवेश करा",
                auth_lbl_pwd: "खरेदी अधिकारी पासवर्ड",
                auth_use_demo: "डेमो आयडी वापरा (`admin123`)",
                auth_btn_officer_login: "प्रमाणित करा आणि गेटवे मध्ये प्रवेश करा",
                btn_login_reg: "लॉगिन / नोंदणी",
                btn_logout: "बाहेर पडा",
                welcome_title: "कृषीसेतू खरेदी हब मध्ये आपले स्वागत आहे",
                welcome_sub: "डिलिव्हरी स्लॉट शेड्यूल करण्यासाठी शेतकरी म्हणून किंवा यार्ड आगमनाचे व्यवस्थापन करण्यासाठी खरेदी अधिकारी म्हणून लॉग इन करा.",
                welcome_btn: "प्रारंभ करा / लॉगिन",
                btn_dl_registry: "सुरक्षित नोंदणी डाउनलोड करा",
                btn_dl_ledger: "सुरक्षित लेजर डाउनलोड करा",
                reg_tab_title: "स्लॉटनुसार नोंदणीकृत शेतकरी",
                reg_tab_sub: "त्यांच्या वाटप केलेल्या वेळेच्या स्लॉटद्वारे वर्गीकृत सर्व शेतकरी बुकिंगचे विहंगावलोकन.",
                assay_title: "तपासणी गुणवत्ता तपासणी",
                assay_desc: "टोकनसाठी ओलावा, शुद्धता आणि धान्याचे मानक तपासा",
                assay_lbl_remarks: "तपासणी निकाल / शेरा",
                assay_btn_good: "चांगले (पास आणि पुढे पाठवा)",
                assay_btn_bad: "वाईट (स्टॉक नाकारा)",
                weigh_title: "वजनकाटाअंती अंतिम मोजमाप",
                weigh_desc: "टोकनसाठी ट्रक/ट्रॉली सत्यापित एकूण वजन प्रविष्ट करा",
                weigh_lbl_weight: "अंतिम सत्यापित वजन (क्विंटल)",
                weigh_help: "MSP पेमेंट या मूल्यावर आधारित त्वरित पुनर्गणित आणि लॉक केले जाईल.",
                weigh_btn_confirm: "वजन पुष्टी करा आणि अनलोडिंगकडे पुढे जा"
            }
        };

        function showAlert(title, message) {
            document.getElementById('alertTitle').innerText = title;
            document.getElementById('alertMessage').innerText = message;
            document.getElementById('validationAlertModal').classList.remove('hidden');
        }

        function closeValidationAlert() {
            document.getElementById('validationAlertModal').classList.add('hidden');
        }

        function formatNum(val, options = {}) {
            if (typeof val !== 'number') val = parseFloat(val);
            if (isNaN(val)) return val;
            const localeMap = { 'en': 'en-IN', 'hi': 'hi-IN', 'mr': 'mr-IN' };
            return val.toLocaleString(localeMap[currentLang] || 'en-IN', options);
        }

        function getCropName(crop) { return (translations[currentLang].crops && translations[currentLang].crops[crop]) ? translations[currentLang].crops[crop] : crop; }

        function changeLanguage(lang) {
            currentLang = lang;
            const t = translations[lang] || translations['en'];
            
            document.querySelectorAll('[data-i18n]').forEach(el => {
                const key = el.getAttribute('data-i18n');
                if (t[key]) {
                    if (el.tagName === 'INPUT' && el.hasAttribute('placeholder')) {
                        el.placeholder = t[key];
                    } else {
                        el.innerHTML = t[key];
                    }
                }
            });

            updateTabVisibility(); 
            if (latestStateData) renderUI(latestStateData);
        }

        function openAuthModal() { document.getElementById('authModal').classList.remove('hidden'); }
        function closeAuthModal() { document.getElementById('authModal').classList.add('hidden'); }

        function switchRoleModal(role) {
            if (role === 'FARMER') {
                document.getElementById('tabRoleFarmer').className = "py-2 rounded-lg bg-emerald-600 text-white transition shadow";
                document.getElementById('tabRoleOfficer').className = "py-2 rounded-lg text-slate-600 hover:text-slate-900 transition";
                document.getElementById('formFarmer').classList.remove('hidden');
                document.getElementById('formOfficer').classList.add('hidden');
            } else {
                document.getElementById('tabRoleOfficer').className = "py-2 rounded-lg bg-slate-900 text-white transition shadow";
                document.getElementById('tabRoleFarmer').className = "py-2 rounded-lg text-slate-600 hover:text-slate-900 transition";
                document.getElementById('formOfficer').classList.remove('hidden');
                document.getElementById('formFarmer').classList.add('hidden');
            }
        }

        function fillDemoOfficerPwd() {
            document.getElementById('officerPassword').value = 'admin123';
        }

        async function requestFarmerOTP() {
            const name = document.getElementById('farmerNameInput').value.trim();
            const mobile = document.getElementById('farmerMobileInput').value.trim();
            
            if (!name) return showAlert("Incomplete Information", "Please enter your name.");
            if (!/^\d{10}$/.test(mobile)) return showAlert("Invalid Mobile Number", "Mobile number must be exactly 10 digits.");

            const res = await fetch('/api/v1/farmer/send-otp', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ phone_number: mobile, farmer_name: name })
            });
            if (res.ok) {
                const data = await res.json();
                document.getElementById('farmerStep1').classList.add('hidden');
                document.getElementById('farmerStep2').classList.remove('hidden');
                document.getElementById('otpDebugHint').innerText = `(Hint OTP: ${data.debug_otp})`;
            } else {
                showAlert("Request Failed", "Failed to send verification OTP.");
            }
        }

        function backToFarmerStep1() {
            document.getElementById('farmerStep2').classList.add('hidden');
            document.getElementById('farmerStep1').classList.remove('hidden');
        }

        async function verifyAndLoginFarmer() {
            const mobile = document.getElementById('farmerMobileInput').value.trim();
            const name = document.getElementById('farmerNameInput').value.trim();
            const otp = document.getElementById('farmerOtpInput').value.trim();

            if (otp.length !== 6) return showAlert("Invalid OTP", "Please enter the 6-digit OTP code.");

            const res = await fetch('/api/v1/farmer/verify-otp', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ phone_number: mobile, otp_code: otp })
            });

            if (res.ok) {
                currentUserRole = 'FARMER';
                currentFarmerPhone = mobile;
                currentFarmerName = name;
                document.getElementById('reg_name').value = name;
                document.getElementById('reg_phone').value = mobile;
                document.getElementById('book_phone').value = mobile;

                closeAuthModal();
                updateTabVisibility();
                switchTab('bookingTab');
                if (latestStateData) renderUI(latestStateData);
            } else {
                showAlert("Authentication Error", "Invalid or expired OTP code!");
            }
        }

        async function loginAsOfficer() {
            const pwd = document.getElementById('officerPassword').value;
            const res = await fetch('/api/v1/officer/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ password: pwd })
            });
            if (res.ok) {
                const data = await res.json();
                officerToken = data.token;
                currentUserRole = 'OFFICER';
                
                closeAuthModal();
                updateTabVisibility();
                switchTab('officerTab');
                document.getElementById('officerPassword').value = '';
                if (latestStateData) renderUI(latestStateData);
            } else { 
                showAlert("Authentication Error", "Invalid Procurement Officer Password!"); 
            }
        }

        function logoutUser() {
            currentUserRole = null;
            currentFarmerPhone = null;
            currentFarmerName = null;
            officerToken = null;
            currentActiveTab = 'marketTab';
            
            updateTabVisibility();
            switchTab('marketTab');
            if (latestStateData) renderUI(latestStateData);
        }

        function updateTabVisibility() {
            const btnLogin = document.getElementById('btnLoginModalTrigger');
            const badge = document.getElementById('userBadge');
            const badgeText = document.getElementById('userBadgeText');
            const notice = document.getElementById('guestLoginNotice');
            const navContainer = document.getElementById('mainTabsNav');
            const t = translations[currentLang] || translations['en'];

            navContainer.innerHTML = '';
            navContainer.innerHTML += `
                <button onclick="switchTab('marketTab')" id="btnMarketTab" class="tab-btn py-2.5 px-3.5 text-slate-400 hover:text-slate-200 border-b-2 border-transparent flex items-center space-x-2">
                    <i class="fa-solid fa-chart-line"></i><span>${t.tab_market}</span>
                </button>
            `;

            if (!currentUserRole) {
                btnLogin.classList.remove('hidden');
                badge.classList.add('hidden');
                notice.classList.remove('hidden');
            } 
            else if (currentUserRole === 'FARMER') {
                btnLogin.classList.add('hidden');
                badge.classList.remove('hidden');
                notice.classList.add('hidden');
                badgeText.innerText = `🌾 ${currentFarmerName || 'Farmer'}`;

                navContainer.innerHTML += `
                    <button onclick="switchTab('bookingTab')" id="btnBookingTab" class="tab-btn py-2.5 px-3.5 text-slate-400 hover:text-slate-200 border-b-2 border-transparent flex items-center space-x-2">
                        <i class="fa-solid fa-user-plus"></i><span>${t.tab_booking}</span>
                    </button>
                    <button onclick="switchTab('trackerTab')" id="btnTrackerTab" class="tab-btn py-2.5 px-3.5 text-slate-400 hover:text-slate-200 border-b-2 border-transparent flex items-center space-x-2">
                        <i class="fa-solid fa-bell text-emerald-400"></i><span class="ml-1 font-bold">Booking Updates & Ledger</span>
                    </button>
                `;
            } 
            else if (currentUserRole === 'OFFICER') {
                btnLogin.classList.add('hidden');
                badge.classList.remove('hidden');
                notice.classList.add('hidden');
                badgeText.innerText = `👮 Procurement Officer`;

                navContainer.innerHTML += `
                    <button onclick="switchTab('officerTab')" id="btnOfficerTab" class="tab-btn py-2.5 px-3.5 text-slate-400 hover:text-slate-200 border-b-2 border-transparent flex items-center space-x-2">
                        <i class="fa-solid fa-user-tie text-amber-400"></i><span>${t.tab_officer}</span>
                    </button>
                    <button onclick="switchTab('registryTab')" id="btnRegistryTab" class="tab-btn py-2.5 px-3.5 text-slate-400 hover:text-slate-200 border-b-2 border-transparent flex items-center space-x-2">
                        <i class="fa-solid fa-users-viewfinder text-blue-400"></i><span>${t.tab_registry}</span>
                    </button>
                    <button onclick="switchTab('queueTab')" id="btnQueueTab" class="tab-btn py-2.5 px-3.5 text-slate-400 hover:text-slate-200 border-b-2 border-transparent flex items-center space-x-2">
                        <i class="fa-solid fa-truck-ramp-box"></i><span>${t.tab_queue}</span>
                    </button>
                    <button onclick="switchTab('trackerTab')" id="btnTrackerTab" class="tab-btn py-2.5 px-3.5 text-slate-400 hover:text-slate-200 border-b-2 border-transparent flex items-center space-x-2">
                        <i class="fa-solid fa-money-check-dollar"></i><span class="ml-1">${t.tab_tracker}</span>
                    </button>
                `;
            }

            const btnMap = { 'marketTab': 'btnMarketTab', 'bookingTab': 'btnBookingTab', 'officerTab': 'btnOfficerTab', 'registryTab': 'btnRegistryTab', 'queueTab': 'btnQueueTab', 'trackerTab': 'btnTrackerTab' };
            if(document.getElementById(btnMap[currentActiveTab])) {
                document.getElementById(btnMap[currentActiveTab]).className = "tab-btn py-2.5 px-3.5 text-amber-400 border-b-2 border-amber-400 font-bold flex items-center space-x-2";
            }
        }

        async function downloadOfficerFile(type) {
            const url = type === 'registry' ? '/api/v1/downloads/officer/registry' : '/api/v1/downloads/officer/ledger';
            try {
                const res = await fetch(url, { headers: { 'Authorization': 'Bearer ' + officerToken } });
                if (!res.ok) throw new Error("Unauthorized");
                const blob = await res.blob();
                const a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = `KrishiSetu_Encrypted_${type}_Statement.csv`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            } catch (e) {
                showAlert("Download Failed", "Unauthorized or Session Expired.");
            }
        }

        function downloadFarmerReceipt(tokenId) {
            const url = `/api/v1/downloads/farmer/receipt/${tokenId}?phone=${currentFarmerPhone}`;
            window.open(url, '_blank');
        }

        async function fetchWithAuth(url, options = {}) {
            if (!options.headers) options.headers = {};
            options.headers['Authorization'] = `Bearer ${officerToken}`;
            options.headers['Content-Type'] = 'application/json';
            const res = await fetch(url, options);
            if (res.status === 401) {
                showAlert("Session Expired", "Please login again.");
                logoutUser();
                openAuthModal();
                throw new Error("401");
            }
            return res;
        }

        async function loadAvailableSlots() {
            try {
                const res = await fetch('/api/v1/slots/available');
                const data = await res.json();
                const select = document.getElementById('book_slot');
                select.innerHTML = '';
                if (data.slots.length === 0) {
                    select.innerHTML = '<option value="">🚨 HOUSE FULL - No Slots Available</option>';
                    select.disabled = true;
                } else {
                    select.disabled = false;
                    data.slots.forEach(s => { select.innerHTML += `<option value="${s.slot}">${s.slot} (${formatNum(s.space_left_qtl)} Qtl Space Left)</option>`; });
                }
            } catch(e) {}
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        const socket = new WebSocket(wsUrl);

        socket.onopen = () => {
            document.getElementById('wsStatus').className = "inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-900 text-emerald-200";
            document.getElementById('wsStatus').innerHTML = `<span class="w-2 h-2 mr-1.5 bg-emerald-400 rounded-full animate-pulse"></span> <span>Live System Sync</span>`;
            loadAvailableSlots();
        };

        socket.onclose = () => {
            document.getElementById('wsStatus').className = "inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-red-900 text-red-200";
            document.getElementById('wsStatus').innerHTML = `<span class="w-2 h-2 mr-1.5 bg-red-400 rounded-full"></span> <span>Offline</span>`;
        };

        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === "STATE_UPDATE") {
                latestStateData = data;
                renderUI(data);
                loadAvailableSlots();
            }
        };

        function switchTab(tabId) {
            if (currentUserRole !== 'OFFICER' && (tabId === 'officerTab' || tabId === 'queueTab' || tabId === 'registryTab')) {
                showAlert("Access Denied", "This tab is restricted to Procurement Officers only.");
                return;
            }
            if (currentUserRole !== 'FARMER' && tabId === 'bookingTab') {
                showAlert("Access Denied", "This tab is restricted to Farmers only.");
                return;
            }
            
            currentActiveTab = tabId;
            
            ['marketTab', 'bookingTab', 'officerTab', 'registryTab', 'queueTab', 'trackerTab'].forEach(t => document.getElementById(t).classList.add('hidden'));
            document.getElementById(tabId).classList.remove('hidden');
            
            document.querySelectorAll('.tab-btn').forEach(btn => btn.className = "tab-btn py-2.5 px-3.5 text-slate-400 hover:text-slate-200 border-b-2 border-transparent flex items-center space-x-2");
            const btnMap = { 'marketTab': 'btnMarketTab', 'bookingTab': 'btnBookingTab', 'officerTab': 'btnOfficerTab', 'registryTab': 'btnRegistryTab', 'queueTab': 'btnQueueTab', 'trackerTab': 'btnTrackerTab' };
            if(document.getElementById(btnMap[tabId])) {
                document.getElementById(btnMap[tabId]).className = "tab-btn py-2.5 px-3.5 text-amber-400 border-b-2 border-amber-400 font-bold flex items-center space-x-2";
            }
        }

        function calcMSP() {
            const crop = document.getElementById('book_crop').value;
            const weight = parseFloat(document.getElementById('book_weight').value) || 0;
            const rates = { "Soybean": 4892.00, "Wheat": 2275.00, "Paddy (Rice)": 2300.00, "Cotton": 7121.00 };
            const total = (rates[crop] || 2000.0) * weight;
            document.getElementById('estMSPText').innerText = `₹${formatNum(total, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        }

        async function registerFarmer() {
            const phone = document.getElementById('reg_phone').value.trim();
            const aadhaar = document.getElementById('reg_aadhaar').value.trim();
            const bank = document.getElementById('reg_bank').value.trim();
            const ifsc = document.getElementById('reg_ifsc').value.trim().toUpperCase();

            if (!/^\d{10}$/.test(phone)) {
                return showAlert("Invalid Mobile Number", "⚠️ Red Alert: Mobile number must be exactly 10 digits.");
            }
            if (!/^\d{4}$/.test(aadhaar)) {
                return showAlert("Invalid Aadhaar Digits", "⚠️ Red Alert: Please enter exactly the last 4 digits of your Aadhaar card.");
            }
            if (!/^\d{9,18}$/.test(bank)) {
                return showAlert("Invalid Bank Account", "⚠️ Red Alert: Bank account number must be correctly filled (9 to 18 digits).");
            }
            if (!/^[A-Z]{4}0[A-Z0-9]{6}$/.test(ifsc) && ifsc.length !== 11) {
                return showAlert("Invalid IFSC Code", "⚠️ Red Alert: IFSC code must be correctly filled with 11 characters.");
            }

            const payload = {
                farmer_name: document.getElementById('reg_name').value.trim(), 
                phone_number: phone,
                aadhaar_last_four: aadhaar, 
                bank_account_no: bank,
                ifsc_code: ifsc, 
                land_area_acres: parseFloat(document.getElementById('reg_land').value) || 0,
                village: document.getElementById('reg_village').value.trim(), 
                total_harvest_stock_qtl: parseFloat(document.getElementById('reg_total_stock').value) || 0,
                procurement_center: document.getElementById('reg_center').value
            };

            const res = await fetch('/api/v1/farmer/register', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload) });
            const data = await res.json();
            if (!res.ok) {
                return showAlert("Registration Error", data.detail || "Failed to register farmer.");
            }

            document.getElementById('book_phone').value = payload.phone_number;
            document.getElementById('regStatus').innerText = `✅ Registered: ${data.farmer.farmer_id} (${data.farmer.procurement_center}) (Stock: ${formatNum(data.farmer.total_harvest_stock_qtl)} Qtl)`;
        }

        async function bookSlot() {
            const phone = document.getElementById('book_phone').value.trim();
            if (!/^\d{10}$/.test(phone)) {
                return showAlert("Invalid Mobile Number", "⚠️ Red Alert: Registered mobile number must be exactly 10 digits.");
            }
            if(!document.getElementById('book_slot').value) {
                return showAlert("Slot Unavailable", "🚨 Red Alert: No slot selected or APMC hub is fully saturated. Please choose an available time window.");
            }

            const payload = {
                farmer_phone: phone, 
                commodity: document.getElementById('book_crop').value,
                weight_to_bring_quintals: parseFloat(document.getElementById('book_weight').value) || 0, 
                vehicle_type: document.getElementById('book_vehicle_type').value,
                vehicle_number: document.getElementById('book_vehicle_no').value.trim(), 
                preferred_slot: document.getElementById('book_slot').value
            };

            const res = await fetch('/api/v1/slots/book', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload) });
            const data = await res.json();
            if (!res.ok) {
                return showAlert("Booking Alert & Duplicate Check", data.detail || "Failed to book slot.");
            }
            currentPassToken = data.token;
            renderPass(data.token);
        }

        function renderPass(token) {
            document.getElementById('passEmpty').classList.add('hidden');
            document.getElementById('passReady').classList.remove('hidden');
            document.getElementById('cardTokenId').innerText = token.token_id;
            document.getElementById('cardFarmer').innerText = `${token.farmer_name} • ${token.vehicle_number}`;
            document.getElementById('cardSlot').innerText = `${token.allocated_slot} (${token.procurement_center})`;
            document.getElementById('cardOfficerStatus').innerText = token.officer_status;
            document.getElementById('cardStage').innerText = token.current_stage;
            const badge = document.getElementById('passStatusBadge');
            if (token.officer_status === "ACCEPTED") { badge.className = "text-[10px] bg-emerald-600 text-white px-2 py-0.5 rounded font-bold uppercase"; badge.innerText = "Approved"; }
            else if (token.officer_status === "REJECTED") { badge.className = "text-[10px] bg-red-600 text-white px-2 py-0.5 rounded font-bold uppercase"; badge.innerText = "Rejected"; }
            else { badge.className = "text-[10px] bg-amber-500 text-slate-900 px-2 py-0.5 rounded font-bold uppercase"; badge.innerText = "Awaiting Approval"; }
            const qrContainer = document.getElementById("cardQRCode");
            qrContainer.innerHTML = "";
            qrCodeInstance = new QRCode(qrContainer, { text: JSON.stringify({ token: token.token_id, farmer: token.farmer_name, status: token.officer_status }), width: 70, height: 70 });
        }

        async function officerDecision(tokenId, decision) {
            await fetchWithAuth('/api/v1/officer/decision', {
                method: 'POST', body: JSON.stringify({ token_id: tokenId, decision: decision, remarks: decision === 'ACCEPT' ? 'Approved by Procurement Desk' : 'Yard Capacity Limit' })
            });
        }

        function handleAdvanceStageClick(tokenId, currentStage, currentWeight) {
            activeModalTokenId = tokenId;
            if (currentStage === 'ASSAYING') {
                document.getElementById('qualityModalToken').innerText = tokenId;
                document.getElementById('qualityModal').classList.remove('hidden');
            } else if (currentStage === 'WEIGHMENT') {
                document.getElementById('weighmentModalToken').innerText = tokenId;
                document.getElementById('weighmentWeightInput').value = currentWeight;
                document.getElementById('weighmentModal').classList.remove('hidden');
            } else {
                executeAdvanceStage(tokenId, null, null, null);
            }
        }

        function closeQualityModal() { document.getElementById('qualityModal').classList.add('hidden'); }
        function closeWeighmentModal() { document.getElementById('weighmentModal').classList.add('hidden'); }

        async function submitQualityCheck(qualityStatus) {
            const remarks = document.getElementById('qualityRemarksInput').value;
            closeQualityModal();
            await executeAdvanceStage(activeModalTokenId, null, qualityStatus, remarks);
        }

        async function submitWeighmentWeight() {
            const weight = parseFloat(document.getElementById('weighmentWeightInput').value);
            if (!weight || weight <= 0) return showAlert("Invalid Weight", "Please enter a verified weight greater than 0.");
            closeWeighmentModal();
            await executeAdvanceStage(activeModalTokenId, weight, null, null);
        }

        async function executeAdvanceStage(tokenId, weight, qualityStatus, qualityRemarks) {
            await fetchWithAuth('/api/v1/mandi/advance-stage', {
                method: 'POST', 
                body: JSON.stringify({ token_id: tokenId, actual_weight: weight, quality_status: qualityStatus, quality_remarks: qualityRemarks })
            });
        }

        async function triggerEmergency(mins, reason) {
            await fetchWithAuth('/api/v1/mandi/emergency-delay', {
                method: 'POST', body: JSON.stringify({ delay_minutes: mins, reason: reason })
            });
        }

        function renderUI(state) {
            document.getElementById('marketInflowTotal').innerText = `${formatNum(state.total_market_arrivals_today)} Qtl`;
            document.getElementById('marketFarmerTotal').innerText = `${formatNum(state.total_farmers)}`;
            document.getElementById('marketActivePasses').innerText = `${formatNum(state.tokens.filter(tk => tk.officer_status === 'ACCEPTED').length)}`;

            const quotaDiv = document.getElementById('stockQuotaGrid');
            quotaDiv.innerHTML = '';
            for (const [crop, data] of Object.entries(state.stock_targets)) {
                const target = data.target_quota_qtl, procured = data.procured_qtl, deficit = Math.max(0, target - procured), pct = Math.min(100, Math.round((procured / target) * 100));
                quotaDiv.innerHTML += `
                    <div class="bg-slate-50 p-4 rounded-xl border border-slate-200">
                        <div class="flex justify-between items-center mb-1">
                            <span class="font-bold text-slate-800">${getCropName(crop)}</span>
                            <span class="text-xs font-mono font-semibold text-emerald-700">${formatNum(pct)}% Met</span>
                        </div>
                        <div class="w-full bg-slate-200 rounded-full h-2 mb-2"><div class="bg-emerald-600 h-2 rounded-full" style="width: ${pct}%"></div></div>
                        <div class="text-[11px] text-slate-500 space-y-0.5">
                            <div class="flex justify-between"><span>Target Quota:</span><span class="font-bold">${formatNum(target)} Qtl</span></div>
                            <div class="flex justify-between"><span>Procured:</span><span class="font-bold text-emerald-600">${formatNum(procured)} Qtl</span></div>
                            <div class="flex justify-between text-amber-800"><span>Required Left:</span><span class="font-bold">${formatNum(deficit)} Qtl</span></div>
                        </div>
                    </div>`;
            }

            const mspDiv = document.getElementById('mspRateGrid');
            mspDiv.innerHTML = '';
            for (const [crop, rate] of Object.entries(state.msp_rates)) {
                mspDiv.innerHTML += `<div class="bg-emerald-50/50 p-3 rounded-xl border border-emerald-100 flex justify-between items-center"><span class="text-xs font-semibold text-slate-700">${getCropName(crop)}</span><span class="text-xs font-bold text-emerald-800 font-mono">₹${formatNum(rate)}/Qtl</span></div>`;
            }

            const officerTbody = document.getElementById('officerTableBody');
            if (state.tokens.length === 0) officerTbody.innerHTML = `<tr><td colspan="6" class="text-center p-8 text-slate-400">No incoming farmer requests awaiting approval.</td></tr>`;
            else {
                officerTbody.innerHTML = '';
                state.tokens.forEach(tk => {
                    let badge = `<span class="bg-amber-100 text-amber-800 px-2 py-0.5 rounded font-bold text-[10px]">Pending Verification</span>`;
                    if (tk.officer_status === "ACCEPTED") badge = `<span class="bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded font-bold text-[10px]">Approved</span>`;
                    if (tk.officer_status === "REJECTED") badge = `<span class="bg-red-100 text-red-800 px-2 py-0.5 rounded font-bold text-[10px]">Rejected</span>`;
                    officerTbody.innerHTML += `
                        <tr class="hover:bg-slate-50 transition">
                            <td class="p-3 font-mono font-bold text-emerald-800">${tk.token_id}<br><span class="text-[10px] text-blue-600 font-semibold">${tk.procurement_center || 'Nagpur Central APMC Yard 01'}</span></td>
                            <td class="p-3 font-semibold">${tk.farmer_name}<br><span class="text-[10px] text-slate-500 font-mono">****${tk.phone_number.slice(-4)}</span></td>
                            <td class="p-3 font-medium"><span class="text-slate-700 font-bold">${getCropName(tk.commodity)}</span><br><span class="text-[10px] text-slate-500">Farm Stock: ${formatNum(tk.total_farm_stock_qtl)} Q | <strong>Brought: ${formatNum(tk.weight_quintals)} Q</strong></span></td>
                            <td class="p-3 font-mono text-slate-700">${tk.allocated_slot}</td>
                            <td class="p-3">${badge}</td>
                            <td class="p-3 text-right">
                                ${tk.officer_status === 'PENDING_APPROVAL' ? `
                                    <div class="flex justify-end space-x-1">
                                        <button onclick="officerDecision('${tk.token_id}', 'ACCEPT')" class="bg-emerald-600 hover:bg-emerald-700 text-white px-2.5 py-1 rounded text-xs font-bold transition"><i class="fa-solid fa-check mr-1"></i> Accept</button>
                                        <button onclick="officerDecision('${tk.token_id}', 'REJECT')" class="bg-red-600 hover:bg-red-700 text-white px-2.5 py-1 rounded text-xs font-bold transition"><i class="fa-solid fa-xmark mr-1"></i> Reject</button>
                                    </div>` : `<span class="text-[11px] text-slate-400 font-medium">Action Logged</span>`}
                            </td>
                        </tr>`;
                });
            }
            
            const registryDiv = document.getElementById('slotRegistryContent');
            if (state.tokens.length === 0) {
                registryDiv.innerHTML = `<div class="text-center py-10 text-slate-400 border border-dashed border-slate-300 rounded-xl">No farmers have registered yet.</div>`;
            } else {
                registryDiv.innerHTML = '';
                const groupedTokens = {};
                for (const slot of Object.keys(state.slot_occupancy)) {
                    groupedTokens[slot] = [];
                }
                state.tokens.forEach(tk => {
                    if (!groupedTokens[tk.allocated_slot]) groupedTokens[tk.allocated_slot] = [];
                    groupedTokens[tk.allocated_slot].push(tk);
                });

                for (const [slot, tks] of Object.entries(groupedTokens)) {
                    let html = `
                    <div class="border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                        <div class="bg-slate-50 px-4 py-3 border-b border-slate-200 flex justify-between items-center">
                            <h3 class="font-bold text-slate-800"><i class="fa-solid fa-clock text-blue-500 mr-2"></i>Slot: ${slot}</h3>
                            <span class="bg-blue-100 text-blue-800 text-xs font-bold px-2.5 py-1 rounded-full">${formatNum(tks.length)} Farmers</span>
                        </div>
                        <div class="p-0 overflow-x-auto">
                            <table class="w-full text-left text-xs">
                                <thead class="bg-white text-slate-500 uppercase border-b border-slate-100">
                                    <tr>
                                        <th class="p-3">Token & Center</th>
                                        <th class="p-3">Farmer Name & Encrypted Contact</th>
                                        <th class="p-3">Commodity & Weight</th>
                                        <th class="p-3">Vehicle</th>
                                        <th class="p-3">Approval Status</th>
                                    </tr>
                                </thead>
                                <tbody class="divide-y divide-slate-100 bg-white">
                    `;
                    if (tks.length === 0) {
                        html += `<tr><td colspan="5" class="p-6 text-center text-slate-400">No bookings currently active for this time slot.</td></tr>`;
                    } else {
                        tks.forEach(tk => {
                            let badgeColor = tk.officer_status === 'ACCEPTED' ? 'bg-emerald-100 text-emerald-800' : (tk.officer_status === 'REJECTED' ? 'bg-red-100 text-red-800' : 'bg-amber-100 text-amber-800');
                            html += `
                            <tr class="hover:bg-slate-50">
                                <td class="p-3 font-mono font-bold text-slate-700">${tk.token_id}<br><span class="text-[10px] text-blue-600 font-semibold">${tk.procurement_center || 'Nagpur Central APMC Yard 01'}</span></td>
                                <td class="p-3 font-semibold">${tk.farmer_name}<br><span class="text-[10px] text-slate-500 font-mono">****${tk.phone_number.slice(-4)}</span></td>
                                <td class="p-3 font-medium">${getCropName(tk.commodity)}<br><span class="text-[10px] text-slate-500">${formatNum(tk.weight_quintals)} Qtl</span></td>
                                <td class="p-3 text-slate-600 font-medium">${tk.vehicle_number} <br><span class="text-[10px] text-slate-500">${tk.vehicle_type}</span></td>
                                <td class="p-3"><span class="px-2 py-0.5 rounded text-[10px] font-bold ${badgeColor}">${tk.officer_status}</span></td>
                            </tr>
                            `;
                        });
                    }
                    html += `</tbody></table></div></div>`;
                    registryDiv.innerHTML += html;
                }
            }

            const capDiv = document.getElementById('capacityBars');
            capDiv.innerHTML = '';
            for (const [slot, booked] of Object.entries(state.slot_occupancy)) {
                const pct = Math.min(100, Math.round((booked / state.max_capacity) * 100)), color = pct > 80 ? 'bg-red-500' : (pct > 50 ? 'bg-amber-500' : 'bg-emerald-500');
                capDiv.innerHTML += `
                    <div class="bg-slate-50 p-3 rounded-xl border border-slate-200">
                        <div class="flex justify-between text-xs font-bold text-slate-700 mb-1"><span>${slot}</span><span>${formatNum(booked)}/${formatNum(state.max_capacity)} Q</span></div>
                        <div class="w-full bg-slate-200 rounded-full h-2 overflow-hidden"><div class="${color} h-2 rounded-full transition-all" style="width: ${pct}%"></div></div>
                    </div>`;
            }

            const mandiTbody = document.getElementById('mandiTableBody');
            const approvedTokens = state.tokens.filter(tk => tk.officer_status === 'ACCEPTED');
            document.getElementById('activeLoadsBadge').innerText = `${formatNum(approvedTokens.length)} Active Vehicles`;

            if (approvedTokens.length === 0) mandiTbody.innerHTML = `<tr><td colspan="5" class="text-center p-8 text-slate-400">Yard is currently clear.</td></tr>`;
            else {
                mandiTbody.innerHTML = '';
                approvedTokens.forEach(tk => {
                    const isDone = tk.current_stage === "COMPLETED" || tk.current_stage === "REJECTED";
                    mandiTbody.innerHTML += `
                        <tr class="hover:bg-slate-50 transition">
                            <td class="p-3 font-mono font-bold text-emerald-800">${tk.token_id}<br><span class="text-[10px] text-blue-600 font-semibold">${tk.procurement_center || 'Nagpur Central APMC Yard 01'}</span></td>
                            <td class="p-3 font-semibold">${tk.farmer_name}<br><span class="text-[10px] text-slate-500 font-normal font-mono">${tk.vehicle_number} (${tk.vehicle_type})</span></td>
                            <td class="p-3"><span class="font-bold">${getCropName(tk.commodity)}</span><br><span class="text-[10px] text-slate-500">${formatNum(tk.weight_quintals)} Qtl</span></td>
                            <td class="p-3"><span class="px-2 py-0.5 rounded text-[10px] font-bold ${isDone ? 'bg-slate-100 text-slate-600' : 'bg-amber-100 text-amber-900'}">${tk.current_stage}</span></td>
                            <td class="p-3 text-right">
                                ${!isDone ? `<button onclick="handleAdvanceStageClick('${tk.token_id}', '${tk.current_stage}',${tk.weight_quintals})" class="bg-slate-900 hover:bg-slate-800 text-white px-3 py-1 rounded text-xs transition">Advance Stage <i class="fa-solid fa-arrow-right ml-1"></i></button>` : `<span class="${tk.current_stage === 'REJECTED' ? 'text-red-600' : 'text-emerald-700'} font-bold text-xs"><i class="fa-solid fa-circle-check mr-1"></i> ${tk.current_stage}</span>`}
                            </td>
                        </tr>`;
                });
            }

            const payTbody = document.getElementById('paymentLedgerBody');
            
            if (currentUserRole === 'OFFICER') {
                document.getElementById('officerLedgerDownload').classList.remove('hidden');
                document.getElementById('th_receipt_action').classList.add('hidden');
            } else {
                document.getElementById('officerLedgerDownload').classList.add('hidden');
                document.getElementById('th_receipt_action').classList.remove('hidden');
            }

            if (state.tokens.length === 0) payTbody.innerHTML = `<tr><td colspan="7" class="text-center p-8 text-slate-400">No transactions recorded yet.</td></tr>`;
            else {
                payTbody.innerHTML = '';
                let displayTokens = state.tokens;
                
                if (currentUserRole === 'FARMER' && currentFarmerPhone) {
                    displayTokens = state.tokens.filter(tk => tk.phone_number === currentFarmerPhone);
                }

                if (displayTokens.length === 0) {
                    payTbody.innerHTML = `<tr><td colspan="7" class="text-center p-8 text-slate-400">No transaction records found for your account.</td></tr>`;
                } else {
                    displayTokens.forEach(tk => {
                        let payBadge = `<span class="bg-amber-100 text-amber-800 px-2 py-0.5 rounded font-bold">Awaiting Clearance</span>`;
                        if (tk.payment_status === "DBT_INITIATED") payBadge = `<span class="bg-blue-100 text-blue-800 px-2 py-0.5 rounded font-bold">DBT Processing</span>`;
                        if (tk.payment_status === "PAYMENT_CREDITED") payBadge = `<span class="bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded font-bold">Credited via DBT</span>`;
                        if (tk.current_stage === "REJECTED") payBadge = `<span class="bg-red-100 text-red-800 px-2 py-0.5 rounded font-bold">Rejected / Stopped</span>`;
                        
                        let actionTd = "";
                        if (currentUserRole === 'FARMER') {
                            if (tk.payment_status === "PAYMENT_CREDITED" || tk.payment_status === "DBT_INITIATED") {
                                actionTd = `<td class="p-3 text-right"><button onclick="downloadFarmerReceipt('${tk.token_id}')" class="bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded font-bold text-xs shadow-sm transition"><i class="fa-solid fa-download mr-1"></i> Receipt</button></td>`;
                            } else {
                                actionTd = `<td class="p-3 text-right text-xs text-slate-400 font-medium">Pending Payout</td>`;
                            }
                        }

                        let accString = currentUserRole === 'OFFICER' ? `****${tk.bank_account_no.slice(-4)}` : tk.bank_account_no;

                        payTbody.innerHTML += `
                            <tr class="hover:bg-slate-50 transition">
                                <td class="p-3 font-mono font-bold">${tk.token_id}<br><span class="text-[10px] text-slate-400 font-normal">${tk.created_at}</span></td>
                                <td class="p-3 font-semibold">${tk.farmer_name}<br><span class="text-[10px] text-slate-500 font-mono">A/C: ${accString} (${tk.ifsc_code})</span></td>
                                <td class="p-3 font-medium"><span class="font-bold">${getCropName(tk.commodity)}</span><br><span class="text-[10px] text-slate-500">${formatNum(tk.weight_quintals)} Qtl</span></td>
                                <td class="p-3"><span class="px-2 py-0.5 rounded bg-slate-100 font-bold text-[10px]">${tk.current_stage}</span></td>
                                <td class="p-3 font-bold text-emerald-700">₹${formatNum(tk.estimated_payout_rs, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                                <td class="p-3">${payBadge}</td>
                                ${actionTd}
                            </tr>`;
                    });
                }
            }

            if (currentPassToken) {
                const refreshed = state.tokens.find(tk => tk.token_id === currentPassToken.token_id);
                if (refreshed) { currentPassToken = refreshed; renderPass(refreshed); }
            }
        }

        updateTabVisibility();
        changeLanguage('en');
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)