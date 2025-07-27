from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import aiosqlite
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

Base = declarative_base()

class Template(Base):
    __tablename__ = "templates"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    sections = relationship("TemplateSection", back_populates="template", cascade="all, delete-orphan")
    prompts = relationship("Prompt", back_populates="template")

class TemplateSection(Base):
    __tablename__ = "template_sections"
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("templates.id"))
    level = Column(Integer, nullable=False)  # 1, 2, 3 for #, ##, ###
    title = Column(String(255), nullable=False)
    content = Column(Text)  # placeholder content
    order_index = Column(Integer, nullable=False)  # for ordering sections
    parent_id = Column(Integer, ForeignKey("template_sections.id"), nullable=True)
    
    template = relationship("Template", back_populates="sections")

class Prompt(Base):
    __tablename__ = "prompts"
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("templates.id"))
    title = Column(String(255), nullable=False)
    generated_content = Column(Text, nullable=False)  # Final markdown content
    created_at = Column(DateTime, default=datetime.now)
    
    template = relationship("Template", back_populates="prompts")
    contents = relationship("PromptContent", back_populates="prompt", cascade="all, delete-orphan")
    gemini_response = relationship("GeminiResponse", back_populates="prompt", uselist=False)

class PromptContent(Base):
    __tablename__ = "prompt_contents" 
    
    id = Column(Integer, primary_key=True, index=True)
    prompt_id = Column(Integer, ForeignKey("prompts.id"))
    section_id = Column(Integer, ForeignKey("template_sections.id"))
    content = Column(Text, nullable=False)
    
    prompt = relationship("Prompt", back_populates="contents")
    section = relationship("TemplateSection")

class GeminiResponse(Base):
    __tablename__ = "gemini_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    prompt_id = Column(Integer, ForeignKey("prompts.id"))
    response_content = Column(Text, nullable=False)
    status = Column(String(50), default="pending")  # pending, completed, error
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)
    
    prompt = relationship("Prompt", back_populates="gemini_response")

# Database configuration
DATABASE_URL = "sqlite+aiosqlite:///./prompt_service.db"

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close() 