from pydantic import BaseModel

class ChatConnectRequest(BaseModel):
    live_id: str
    platform: str