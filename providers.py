import requests, json, os

class Whatsapp:

    def __init__(self):
        self.API_VERSION        = os.getenv("WP_API_VERSION") 
        self.PHONE_NUMBER_ID    = os.getenv("WP_PHONE_NUMBER_ID")  
        self.ACCESS_TOKEN       = os.getenv("WP_ACCESS_TOKEN")
        self.ID_FIELD           = os.getenv("WP_MESSAGE_ID_FIELD")   

    def send(self, user_phone_number: str, text:str, link_preview: bool):
        try:
            url = f"https://graph.facebook.com/{self.API_VERSION}/{self.PHONE_NUMBER_ID}/messages"
            headers = {
                "Authorization": f"Bearer {self.ACCESS_TOKEN}",
                "Content-Type": "application/json"
            }
            data = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": user_phone_number,
                "type": "text",
                "text": {
                    "preview_url": link_preview,
                    "body": text
                }
            }

            if res := requests.post(url, headers=headers, data=json.dumps(data)):
                return res.json()["messages"][0]['id'], self.ID_FIELD
            else:
                raise Exception(f"the request got response as: {res.json()}" )
            

            
        except Exception as e:
            raise Exception(f"{__class__.__name__}.{self.send.__name__}() failed, Error: {e}")


