from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from datetime import datetime
from utils import GoogleSheets, Genai, Operations
from dotenv import load_dotenv
import os, requests as req  

# OBJECTS
load_dotenv()
app = FastAPI()
GOOGLE_SHEETS = GoogleSheets()

GENAI = Genai()
OPERATIONS = Operations()

# VARIABLES
VERIFY_TOKEN = os.getenv("WP_WEBHOOK_TOKEN")
GS_STATUS_FIELD = os.getenv("GOOGLE_SHEETS_STATUS_FIELD")
GS_PHONE_NUMBER_FIELD = os.getenv("GOOGLE_SHEETS_PHONENUMBER_FIELD")
GS_TIME_STAMP_FIELD = os.getenv("GOOGLE_SHEETS_TIME_STAMP_FIELD")
INTRODUCTION_GAP_SECOND = int(os.getenv("WP_INTRODUCTION_GAP_SEC"))
WP_MESSAGE_ID_FIELD = os.getenv("WP_MESSAGE_ID_FIELD")

# Connect to Google Sheeet
GS_SHEET_NAME        = os.getenv("GOOGLE_SHEETS_SHEET_NAME")
GS_WORK_SHEET_NAME   = os.getenv("GOOGLE_SHEETS_WORK_SHEET_NAME")
SHEET = GOOGLE_SHEETS.get_sheet(GS_SHEET_NAME, GS_WORK_SHEET_NAME)

@app.post("/introduction")
async def run_agent(request: Request):
    """
    GET send introduction messages
    """
    body = await request.json()
    providers = body.get("providers", [])

    if not providers:
        raise HTTPException(status_code=400, detail="Missing providers field!")
    try:
        OPERATIONS.send_Introduction(providers, SHEET, GENAI)

        data = {"status": 200, "details": "Introduction been send"}
        return JSONResponse(content=data, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Webhook verifier required by Meta
@app.get("/", response_class=PlainTextResponse)
async def verify_webhook(request: Request):
    """
    GET route for webhook verification (Facebook / Instagram style)
    """
    params = request.query_params
    mode = params.get("hub.mode")
    challenge = params.get("hub.challenge")
    token = params.get("hub.verify_token")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("WEBHOOK VERIFIED")
        return challenge or ""
    else:
        raise HTTPException(status_code=403, detail="Forbidden")

# Webhook for Whatsapp gets info about message details, and route to required functions 
@app.post("/")
async def receive_webhook(request: Request):
    """
    POST route for receiving webhook events
    """
    body = await request.json()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n\nWebhook received {timestamp}\n")
    try:
        values = body["entry"][0]["changes"][0]["value"]       

        # Status Update Webhook
        try:
            if "statuses" in values:
                status  = values["statuses"][0]["status"]
                message_id = values["statuses"][0]["id"]
                id = int(values["statuses"][0]["recipient_id"])
            
                SHEET.update_cell(GS_PHONE_NUMBER_FIELD, id, GS_STATUS_FIELD, status, {WP_MESSAGE_ID_FIELD: message_id})

                if status == "read":
                    
                    unix_timestamp = int(datetime.now().timestamp())
                    record = SHEET.get_records_by({
                        str(GS_PHONE_NUMBER_FIELD): id
                    })[0]

                    if record.get(GS_STATUS_FIELD) != "answered":

                        time_gap = abs(unix_timestamp - record.get(GS_TIME_STAMP_FIELD, unix_timestamp)) # Calculate the gap between 'delivered' and 'read' stasuses, if somehow sheet doesnt contain time_stamp the gap will be 0 allway

                        if time_gap >= INTRODUCTION_GAP_SECOND:
                            OPERATIONS.send_Attention_Mes(record, "wp", SHEET, GENAI)
        except Exception as e:
            raise Exception(f"the Status Hook have issue; ", e)
        if "messages" in values:
            message_id = values["messages"][0]["id"]
            id = values["messages"][0]["from"]
            pass
            

    except Exception as e:
        print(f"The error raised at POST endpoint of webhook Error: ", e)

    print(body)
    return PlainTextResponse(status_code=200)