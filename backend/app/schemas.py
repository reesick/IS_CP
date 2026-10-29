from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

class ProtectRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    method: Literal['diffusionguard'] = 'diffusionguard'
    profile: Literal['research', 'smoke'] = 'smoke'
    mask_id: str
    watermark: Literal[False] = False
    seed: int = Field(default=42, ge=0, le=2147483647)
    epsilon: float = Field(default=4/255, ge=1/255, le=16/255)

class EditRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    protection_job_id: str
    mask_id: str
    prompt: str = Field(min_length=1, max_length=500)
    editor: Literal['sd15_inpaint'] = 'sd15_inpaint'
    seeds: list[int] = Field(default=[42], min_length=1, max_length=3)
    channel: Literal['local_png', 'jpeg_simulation'] = 'local_png'

class Score(BaseModel):
    requested_edit_completed: Literal['yes','no','uncertain']
    realism: int = Field(ge=1,le=5)
    retained_subject_fidelity: int = Field(ge=1,le=5)

class PairReview(BaseModel):
    seed: int
    clean: Score
    protected: Score

class ReviewRequest(BaseModel):
    pairs: list[PairReview] = Field(min_length=1,max_length=3)
    notes: str = Field(default='',max_length=2000)
