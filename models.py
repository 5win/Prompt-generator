from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class TemplateSectionCreate(BaseModel):
    level: int
    title: str
    content: Optional[str] = ""
    order_index: int
    parent_id: Optional[int] = None

class TemplateSectionResponse(BaseModel):
    id: int
    level: int
    title: str
    content: Optional[str]
    order_index: int
    parent_id: Optional[int]
    
    class Config:
        from_attributes = True

class TemplateCreate(BaseModel):
    title: str
    sections: List[TemplateSectionCreate]

class TemplateResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    sections: List[TemplateSectionResponse]
    
    class Config:
        from_attributes = True

class TemplateListResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class PromptContentCreate(BaseModel):
    section_id: int
    content: str

class PromptCreate(BaseModel):
    template_id: int
    title: str
    contents: List[PromptContentCreate]

class PromptContentResponse(BaseModel):
    id: int
    section_id: int
    content: str
    section: TemplateSectionResponse
    
    class Config:
        from_attributes = True

class PromptResponse(BaseModel):
    id: int
    template_id: int
    title: str
    generated_content: str
    created_at: datetime
    contents: List[PromptContentResponse]
    
    class Config:
        from_attributes = True

class PromptListResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    has_gemini_response: bool
    gemini_status: Optional[str]
    
    class Config:
        from_attributes = True

class GeminiResponseCreate(BaseModel):
    prompt_id: int

class GeminiResponseResponse(BaseModel):
    id: int
    prompt_id: int
    response_content: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True 