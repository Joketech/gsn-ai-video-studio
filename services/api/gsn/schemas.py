from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Credentials(Strict):
    email: str = Field(min_length=5, max_length=254, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    password: str = Field(min_length=12, max_length=128)
    workspace: str = Field(default='GSN Studio', min_length=1, max_length=120)

class Project(Strict):
    name: str = Field(min_length=1, max_length=120)
    brief: str = Field(default='', max_length=5000)

class Consent(Strict):
    subject: str = Field(min_length=1, max_length=200)
    scope: Literal['appearance', 'voice']
    evidence_asset_id: str
    expires_at: str
    commercial_use: bool = False
    attestation: Literal[True]

class Profile(Strict):
    name: str = Field(min_length=1, max_length=120)
    consent_id: str
    reference_asset_ids: list[str] = Field(min_length=1, max_length=20)

class Scene(Strict):
    project_id: str
    script: str = Field(min_length=1, max_length=10000)
    setting: str = Field(default='', max_length=2000)
    camera: Literal['static', 'pan', 'dolly', 'orbit'] = 'static'
    seconds: int = Field(default=5, ge=1, le=30)
    character_id: str | None = None
    voice_id: str | None = None
    commercial: bool = False

class Render(Strict):
    scene_id: str
    request_key: str = Field(min_length=8, max_length=80)

class AgentTask(Strict):
    project_id: str
    role: str
    instruction: str = Field(min_length=1, max_length=5000)
