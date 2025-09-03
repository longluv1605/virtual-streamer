from pydantic import BaseModel

class ChatValidateRequest(BaseModel):
    live_id: str
    platform: str