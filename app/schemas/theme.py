from pydantic import BaseModel

class ThemePresetPayload(BaseModel):
    name: str
    properties_json: str

class ThemePresetResponse(BaseModel):
    id: str
    name: str
    properties_json: str
    is_active: bool
