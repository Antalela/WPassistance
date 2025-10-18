from google.oauth2.service_account import Credentials
from phonenumbers import geocoder, timezone
from zoneinfo import ZoneInfo
from datetime import datetime
from providers import Whatsapp
from google import genai
from google.genai import types
from pydantic import BaseModel

import json, gspread, phonenumbers, os, time

class Operations:
    

    def __init__(self):
        self.PROVIDERS = {
        "wp": Whatsapp()
        }
        self.PHONE_NUMBER_FIELD = os.getenv("GOOGLE_SHEETS_PHONENUMBER_FIELD")
        self.NAME_FIELD = os.getenv("GOOGLE_SHEETS_NAME_FIELD")
        self.CHAT_HISTORY_FIELD = os.getenv("WP_CHAT_HISTORY_FIELD")

    @staticmethod
    def get_number_data(number: str):
        number = number if "+" in number else f"+{number}"

        parsed_number = phonenumbers.parse(number)
        zone = timezone.time_zones_for_geographical_number(parsed_number)
        tz = ZoneInfo(zone[0]) 

        country = geocoder.country_name_for_number(parsed_number, "en")
        country_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M")
        
        return country, country_time

    def send_message(self,phone_number, provider, text, sheet, system_instruction, output_structure, genai, chat_history = None):

        message_text, meta_data = genai.generate_message(text, system_instruction, output_structure)

        message_id, message_id_field = provider.send(phone_number, message_text, False)

        sheet.update_cell(
            self.PHONE_NUMBER_FIELD, 
            phone_number, 
            message_id_field, 
            message_id)
        
        new_part = [{
            "role": "user",
            "parts": [
                {"text": ""}
            ]
        }, 
        {
            "role": "model",
            "parts": [
                {"text": f"{message_text}"}
                ]
        }]

        if chat_history:
            chat_history = json.loads(chat_history)
            chat_history.extend(new_part)
        else:
            chat_history = new_part 


        sheet.update_cell(
            self.PHONE_NUMBER_FIELD, 
            phone_number, 
            self.CHAT_HISTORY_FIELD, 
            json.dumps(chat_history))

    def send_Introduction(self, providers, sheet, genai):
        # Çıktı formatı 
        class Data(BaseModel):
            message: str

        system_instruction = """
            We are Longavita a company that provides vitamin products to our customers, improving their quality of life and health. Prepare an introductory message to establish a dialogue with our potential customer, to introduce our company and products. The language you use should target our customer. Use imput data (JSON) to personalize introduction message!

            ⸻

            Message Style
            •	Tone: Friendly, approachable, and efficient. Use light humor when natural but stay professional.
            •	Clarity: Use short, structured sentences with bullet points or numbered lists when helpful.
            •	Efficiency: Minimize unnecessary back-and-forth by collecting multiple details together when possible.
            •	Personalization: Use the user’s name and data where relevant.
            •	Privacy: Mask sensitive information like emails or addresses in summaries (e.g., jo***@example.com).

            ⸻

            Key Rules
            •	Always give the user a next step to keep the conversation flowing.
            •	Do not add extra field,variables, and placeholders such as [your_prodact_name] to message! use only provided info.
            •	The language you use should target our customer. Input propt will provide a customer phone number, use the area code of number to identify the customer's language and use that to generate a message.
        """

            # Get all customers where Status is equal to None or "" 
        
        customers = sheet.get_records_by({
            "Status":None
        })

        for prov in providers:
            if provider := self.PROVIDERS.get(prov):
            
                for customer in customers:
                    phone_number    = str(customer.get(self.PHONE_NUMBER_FIELD))
                    name            = customer.get(self.NAME_FIELD) 
                    country, country_time = self.get_number_data(phone_number)

                    chat_history = customer.get(self.CHAT_HISTORY_FIELD, "")

                    text = json.dumps({
                        "name": name,
                        "country": country,
                        "time": country_time,                   
                        "chat_history": chat_history
                    })

                    self.send_message(phone_number, provider, text, sheet, system_instruction, Data, genai, chat_history)

    async def send_Attention_Mes(self, customer, provider, sheet, genai):
        time.sleep(5)
        # Çıktı formatı 
        class Data(BaseModel):
            message: str

        system_instruction = """
            It seems we haven't managed to catch the attention of our customer with the our introduction message that you can see on chat_history. They read our message but didn't respond. Let's make one last attempt, but this time we need to succeed in attracting their interest!

            ⸻

            Message Style
            •	Tone: Friendly, approachable, and efficient. Use light humor when natural but stay professional.
            •	Clarity: Use short, structured sentences with bullet points or numbered lists when helpful.
            •	Efficiency: Minimize unnecessary back-and-forth by collecting multiple details together when possible.
            •	Personalization: Use the user’s name and data where relevant.
            •	Privacy: Mask sensitive information like emails or addresses in summaries (e.g., jo***@example.com).

            ⸻

            Key Rules
            •	Always give the user a next step to keep the conversation flowing.
            •	Do not add extra field,variables, and placeholders such as [your_prodact_name] to message! use only provided info.
            •	The language you use should target our customer. Input propt will provide a customer phone number, use the area code of number to identify the customer's language and use that to generate a message.
        """

            # Get all customers where Status is equal to None or "" 
        
        provider = self.PROVIDERS.get(provider)
            
        phone_number    = str(customer.get(self.PHONE_NUMBER_FIELD))
        name            = customer.get(self.NAME_FIELD) 
        country, country_time = self.get_number_data(phone_number)

        chat_history = customer.get(self.CHAT_HISTORY_FIELD, "")

        text = json.dumps({
            "name": name,
            "country": country,
            "time": country_time,                   
            "chat_history": chat_history
        })

        self.send_message(phone_number, provider, text, sheet, system_instruction, Data, genai, chat_history)
       
        

class GoogleSheets:
    # Path to your downloaded service account key
    """
    SERVICE_CRED_DICT = {
    "type": "service_account",
    "project_id": "wp-automation-475117",
    "private_key_id": "05ac5b238d5f3304f3ca48ac24afaaec9e5fc842",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQCpjq4ZabpLeBK8\nJeLKgQ1uIju45YMUq77jj84Wk1UgosdUxw3YsfRf9KyYabKnzOC8k5p0IeJyrSR5\nafxqpHSeZKPqxEX/rntUFE2YiyGLKGmklVkIz6YzRzFk0ANBd3U3V1Lh+mzNOYm3\nRYhDVFYZ+Ktzq4i9D9X5dVubD/JXfatamncXXJHd0p/sdc+cRmM+rlWt6zeuSWYj\nGewKqeRxAtCfC2FxTVdxYGXCE9KooahH84VJzQoEvCqAKRUWaTzILMFjvB2DUA/V\nhUIGCOnog9Tryhp+6gICtn/EpAlUSBPMI9CVj4/9MnaHlOzROgdekVjRtDVv11OM\nSwdoKSlJAgMBAAECggEADGsm1TWpL13cAWvE8JADK83WEfS9ZQYvNPuTXJPt6DYD\n43Gw0e42t9Bz07XqH+Ahla454ceZjkygH0Rj+GuTHwa/+rHlbpSY88+I32NRUZ/k\nHOnTW5HZ2mecdoXFt0XIkAUVTPfKgD12mLW/BS9oHv7Xj+FAYpiGU38E9pZ0aXPs\nDGDZM1zDK3wOF5HIqeGqx+NQfvUrTEYYdXyououVfYHwh3k3we1IZRXpfcMZSNDY\ns55KGccv7ZN44UHZj+mbXTLo1lixDTxbxQcUxefQ2Ne5ogta0GNoByz+pELF5ATX\nOnUcOvp7gG1kB/pJ6Q3U0smlSllC0Ai37Vv8cU73AQKBgQDujZPx8SRmJUf2VrW6\n8l2fg3t0You8d+CzSR8ZEb4to4JtyRIWjpbarNATUzOrNK9/k4MsWR+VmctFkuuh\ngXx9xuohzNNKCyLm8/VoaoKdIfGUduEGi8HaOHgLsrplnXua9FdAzMRLT4jbBQBX\nz8Tf3CVZ8JMGEJSemt4E5eDgZwKBgQC19UwyJsE1hWILhmWdbZ/7iqkL1wR7IrU/\nCKPhGEObAt2BDcYiLz54X/Xxz3vwNEJKmZzXqBNWTAomYZMPpdKLcSOU2xg32L2+\n/mxXNU55HSdz/S2DHDY2lew5H32T/egIPYp/kPgmOtdzHfoHLJCS/xcVtNVjyHV7\nchIIoGTazwKBgQClIKF5R1fP0RyoG0t+lchS45uwa4qYsk57LDF3k/2V7+oX/qgj\nrx4jTp5V0jEg4L5ezAhvyV2Am83GYjXzPQOkuO1W6kaTqXPGdLa6SYgSJu3nvAZ2\nFoXgfVgzmMtIDaQDFgHT3CpAi1SLb0HWhv6bivLb+Bh9iTqnM0JeF5X7HwKBgBKC\nqMS1UpRqREYd3vp763mAaqAMuKT6K+wEqf89I6uCSBxX1V8m5TkDshZuYBJYjqHe\nLKl3rLfrtmCfLoG6Acgzs0XyX+1WfD8QzN62SoxhneDb0aRz20QETmqlPHYwr0kf\nUZaWndftxnssgoH2U6LQln2bztV+0AzF1vXPs1LbAoGBAK36zlX4uOhY/gN2g22b\nf24ljdceDfetkbObOCVLNINj+VpZtW7DmLVYg5mLhxZ0NXbrV3PSw8bV39J64mzP\n+jCW5oNmQkjIhyQiexW+ZH5r40JT+D8AgXufniXgyH1sacuA9iH4bxS+1roOPbbW\n3B3hzAXGV+jUYwvNFQuLdKnu\n-----END PRIVATE KEY-----\n",
    "client_email": "google-sheets@wp-automation-475117.iam.gserviceaccount.com",
    "client_id": "109454853175917774556",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/google-sheets%40wp-automation-475117.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
    }
    """



    # Scopes define what the app can access
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    

    def __init__(self):
        self.SERVICE_CRED_DICT = json.loads(os.environ["GOOGLE_CREDS_JSON"])
        
    def get_sheet(self, sheet_name, work_sheet):
        try:
            # Authenticate and create a client
            creds = Credentials.from_service_account_info(
                self.SERVICE_CRED_DICT, 
                scopes=self.SCOPES
            )
            client = gspread.authorize(creds)

            # Open the sheet by name
            self.sheet = client.open(sheet_name).worksheet(work_sheet) # or .worksheet("Sheet1")
            return self
        except Exception as e:
            raise Exception(f"{__class__.__name__}.{self.get_sheet.__name__}() failed, Error: {e}")

    def get_records_by(self, filters = {}):
        records = self.sheet.get_all_records(default_blank= None)
        try:
            output = []
            for record in records:
            
                # Check for filters
                for key,val in filters.items():
                    if key in record and record[key] == val:
                        # Check for non valid str's
                        record = {
                            key: (None if val in ["null",""] else val)
                            for key, val in record.items()
                        }        
                
                        output.append(record)

            return output
        except Exception as e:
            raise Exception(f"{__class__.__name__}.{self.get_records_by.__name__}() failed, Error: {e}")                    

    def update_cell(self, id_column, id, column_to_update, new_value, filters = {}):
        """
        Updates 'column_to_update' column with 'new_value' where 'id_column' == 'record_id'.
        """
        try:
            # Get all data (including header)
            all_values = self.sheet.get_all_values()
            columns = all_values[0]
            filters_cols = None

            # Get column indexes (1-based for gspread)
            try:
                id_col = columns.index(id_column) + 1
                upd_col = columns.index(column_to_update) + 1

                if filters:
                    filters_cols = {
                        key : columns.index(key) + 1
                        for key,_ in filters.items()
                    }

            except ValueError as e:
                raise Exception(f"Required columns ('{id_column}', '{column_to_update}') not found in sheet. Error: {e}")

            # Find row with matching id
            for row_idx, row in enumerate(all_values[1:], start=2):  # start=2 for 1-based + header row
                if str(row[id_col - 1]) == str(id):

                    if filters_cols:
                        if not all(True for key, col in filters_cols.items() if str(row[col -1] == str(filters[key]))):
                            return False

                    # Update the column_to_update cell
                    self.sheet.update_cell(row_idx, upd_col, new_value)
                    return True

            return f"No record found with '{id_column}'={id}"

        except Exception as e:
            raise Exception(e)


# TODO:
#  - Whatsapp message len() can be max 4096 
class Genai():

  # Kullanılacak olan parametre ve değişkeneler
  
  MODEL_ID = "gemini-2.0-flash" 
  client = None
  chat = None
  safety_settings = None

  def __init__(self):
    GOOGLE_API_KEY: str = os.getenv("GENAI_TOKEN")
    self.client = genai.Client(api_key=GOOGLE_API_KEY)
    self.safety_settings = [
        types.SafetySetting(
            category="HARM_CATEGORY_DANGEROUS_CONTENT", # "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT","HARM_CATEGORY_CIVIC_INTEGRITY"
            threshold="BLOCK_ONLY_HIGH",
        ),
        types.SafetySetting(
            category= "HARM_CATEGORY_HARASSMENT", 
            threshold="BLOCK_ONLY_HIGH",
        ),
        types.SafetySetting(
            category= "HARM_CATEGORY_HATE_SPEECH", 
            threshold="BLOCK_ONLY_HIGH",
        ),
        types.SafetySetting(
            category= "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            threshold="BLOCK_ONLY_HIGH",
        ),
    ]

  def chat_message(self, prompt, sys_instruction, res_schema, chat_history = None):
    try:

      self.chat = self.client.chats.create(
        model= self.MODEL_ID,
        config= types.GenerateContentConfig( # The doc of parametres -> https://googleapis.github.io/python-genai/genai.html#genai.types.GenerateContentConfig
            system_instruction= sys_instruction,
            safety_settings= self.safety_settings,
            temperature= 0.3, # default: 0.4
            top_p= 0.75, # default: 0.95
            top_k= 10, # default: 20
            candidate_count= 1,
            presence_penalty= 1,
            frequency_penalty= 1,
            response_mime_type= 'application/json',
            response_schema= res_schema,
        ),
        history= chat_history
      )

      response = self.chat.send_message(prompt)

      meta_data  = {}
      meta_data['input_tokens'] = getattr(response.usage_metadata, 'prompt_token_count', None)
      meta_data['output_tokens'] = getattr(response.usage_metadata, 'candidates_token_count', None)

      if json_data := json.loads(response.text):
        return json_data, meta_data
      
      raise Exception("non-valid response from genai chat")

    except Exception as e:
      print(f"❗ Genai chat Error: {e}")
      return None

  def generate_message(self, prompt, sys_instruction, res_schema):
    try:

      response = self.client.models.generate_content(
        model= self.MODEL_ID,
        contents= prompt,
        config= types.GenerateContentConfig( # The doc of parametres -> https://googleapis.github.io/python-genai/genai.html#genai.types.GenerateContentConfig
            system_instruction= sys_instruction,
            safety_settings= self.safety_settings,
            temperature= 0.3, # default: 0.4
            top_p= 0.75, # default: 0.95
            top_k= 10, # default: 20
            candidate_count= 1,
            presence_penalty= 1,
            frequency_penalty= 1,
            response_mime_type= 'application/json',
            response_schema= res_schema,
        )
      )

      json_data = json.loads(response.text)

      meta_data  = {}
      meta_data['input_tokens'] = getattr(response.usage_metadata, 'prompt_token_count', None)
      meta_data['output_tokens'] = getattr(response.usage_metadata, 'candidates_token_count', None)

      if message := json_data.get("message"):
          return message, meta_data
        
      raise Exception("non-valid response from genai")
      

    except Exception as e:
      print(f"❗ Genai Error: {e}")
      return None

  # ---- Chat History to JSON.str ----
  @staticmethod
  def chat_history_to_str(chat_history):
      data =  [
          {
              "role": item.role,
              "parts": [{"text": p.text} for p in item.parts],
          }
          for item in chat_history
      ]
      return json.dumps(data)

  # ---- JSON to Chat History ----
  @staticmethod
  def json_to_chat_history(json_history):
      restored = []
      for item in json_history:
          parts = [types.Part(text=p["text"]) for p in item["parts"]]
          if item["role"] == "user":
              restored.append(types.UserContent(parts=parts))
          else:
              restored.append(types.Content(parts=parts, role="model"))
      return restored