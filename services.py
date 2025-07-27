from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import Template, TemplateSection, Prompt, PromptContent, GeminiResponse
from models import TemplateCreate, PromptCreate


class TemplateService:
    @staticmethod
    async def create_template(db: AsyncSession, template_data: TemplateCreate) -> Template:
        # Create template
        template = Template(title=template_data.title)
        db.add(template)
        await db.flush()  # Get template.id

        # Create sections
        for section_data in template_data.sections:
            section = TemplateSection(
                template_id=template.id,
                level=section_data.level,
                title=section_data.title,
                content=section_data.content,
                order_index=section_data.order_index,
                parent_id=section_data.parent_id
            )
            db.add(section)

        await db.commit()

        # 관계된 데이터를 다시 조회해서 반환
        result = await db.execute(
            select(Template)
            .options(selectinload(Template.sections))
            .where(Template.id == template.id)
        )
        return result.scalar_one()

    @staticmethod
    async def get_templates(db: AsyncSession) -> List[Template]:
        result = await db.execute(
            select(Template)
            .options(selectinload(Template.sections))
            .order_by(Template.created_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def get_template_by_id(db: AsyncSession, template_id: int) -> Optional[Template]:
        result = await db.execute(
            select(Template)
            .options(selectinload(Template.sections))
            .where(Template.id == template_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_template(db: AsyncSession, template_id: int, template_data: TemplateCreate) -> Optional[Template]:
        template = await TemplateService.get_template_by_id(db, template_id)
        if not template:
            return None

        # Update template title
        template.title = template_data.title
        template.updated_at = datetime.now()

        # Delete existing sections
        await db.execute(delete(TemplateSection).where(TemplateSection.template_id == template_id))

        # Create new sections
        for section_data in template_data.sections:
            section = TemplateSection(
                template_id=template.id,
                level=section_data.level,
                title=section_data.title,
                content=section_data.content,
                order_index=section_data.order_index,
                parent_id=section_data.parent_id
            )
            db.add(section)

        await db.commit()

        # 관계된 데이터를 다시 조회해서 반환
        result = await db.execute(
            select(Template)
            .options(selectinload(Template.sections))
            .where(Template.id == template.id)
        )
        return result.scalar_one()

    @staticmethod
    async def delete_template(db: AsyncSession, template_id: int) -> bool:
        template = await TemplateService.get_template_by_id(db, template_id)
        if not template:
            return False

        await db.delete(template)
        await db.commit()
        return True


class PromptService:
    @staticmethod
    async def create_prompt(db: AsyncSession, prompt_data: PromptCreate) -> Prompt:
        # Get template for markdown generation
        template = await TemplateService.get_template_by_id(db, prompt_data.template_id)
        if not template:
            raise ValueError("Template not found")

        # Generate markdown content
        markdown_content = await PromptService.generate_markdown(template, prompt_data.contents)

        # Create prompt
        prompt = Prompt(
            template_id=prompt_data.template_id,
            title=prompt_data.title,
            generated_content=markdown_content
        )
        db.add(prompt)
        await db.flush()

        # Create prompt contents
        for content_data in prompt_data.contents:
            content = PromptContent(
                prompt_id=prompt.id,
                section_id=content_data.section_id,
                content=content_data.content
            )
            db.add(content)

        await db.commit()

        # 관계된 데이터를 다시 조회해서 반환
        result = await db.execute(
            select(Prompt)
            .options(
                selectinload(Prompt.contents).selectinload(PromptContent.section),
                selectinload(Prompt.template)
            )
            .where(Prompt.id == prompt.id)
        )
        return result.scalar_one()

    @staticmethod
    async def generate_markdown(template: Template, contents_data: List) -> str:
        # Create a mapping of section_id to content
        content_map = {content.section_id: content.content for content in contents_data}

        # Sort sections by order_index
        sections = sorted(template.sections, key=lambda x: x.order_index)

        markdown_lines = []

        for section in sections:
            # Add markdown header based on level
            header = "#" * section.level
            markdown_lines.append(f"{header} {section.title}")

            # Add content if exists
            if section.id in content_map and content_map[section.id].strip():
                markdown_lines.append(content_map[section.id])
            elif section.content and section.content.strip():
                # Use placeholder content if no user content provided
                markdown_lines.append(section.content)

            markdown_lines.append("")  # Add empty line

        return "\n".join(markdown_lines).strip()

    @staticmethod
    async def get_prompts(db: AsyncSession) -> List[Prompt]:
        result = await db.execute(
            select(Prompt)
            .options(selectinload(Prompt.gemini_response))
            .order_by(Prompt.created_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def get_prompt_by_id(db: AsyncSession, prompt_id: int) -> Optional[Prompt]:
        result = await db.execute(
            select(Prompt)
            .options(
                selectinload(Prompt.contents).selectinload(PromptContent.section),
                selectinload(Prompt.template),
                selectinload(Prompt.gemini_response)
            )
            .where(Prompt.id == prompt_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def delete_prompt(db: AsyncSession, prompt_id: int) -> bool:
        # 프롬프트가 존재하는지 확인
        result = await db.execute(select(Prompt).where(Prompt.id == prompt_id))
        prompt = result.scalar_one_or_none()
        if not prompt:
            return False

        # 관련된 PromptContent와 GeminiResponse들을 먼저 삭제
        await db.execute(delete(PromptContent).where(PromptContent.prompt_id == prompt_id))
        await db.execute(delete(GeminiResponse).where(GeminiResponse.prompt_id == prompt_id))

        # 프롬프트 삭제
        await db.execute(delete(Prompt).where(Prompt.id == prompt_id))
        await db.commit()

        return True


class GeminiService:
    @staticmethod
    async def create_gemini_response(db: AsyncSession, prompt_id: int) -> GeminiResponse:
        # Check if response already exists
        result = await db.execute(
            select(GeminiResponse).where(GeminiResponse.prompt_id == prompt_id)
        )
        existing_response = result.scalar_one_or_none()

        if existing_response:
            return existing_response

        # Create new response record
        gemini_response = GeminiResponse(
            prompt_id=prompt_id,
            response_content="",
            status="pending"
        )
        db.add(gemini_response)
        await db.commit()
        await db.refresh(gemini_response)

        return gemini_response

    @staticmethod
    async def update_gemini_response(db: AsyncSession, response_id: int, content: str, status: str) -> Optional[
        GeminiResponse]:
        result = await db.execute(
            select(GeminiResponse).where(GeminiResponse.id == response_id)
        )
        response = result.scalar_one_or_none()

        if not response:
            return None

        response.response_content = content
        response.status = status
        if status == "completed":
            response.completed_at = datetime.now()

        await db.commit()
        await db.refresh(response)
        return response
