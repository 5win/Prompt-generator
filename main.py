import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, create_tables
from gemini_client import gemini_client
from models import *
from services import TemplateService, PromptService, GeminiService


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await create_tables()
    yield
    # Shutdown (if needed)


app = FastAPI(title="프롬프트 템플릿 생성 서비스", lifespan=lifespan)

# 정적 파일과 템플릿 설정
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# HTML 페이지 라우트
@app.get("/", response_class=HTMLResponse)
async def main_page(request: Request):
    """메인 페이지"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/templates", response_class=HTMLResponse)
async def templates_page(request: Request, db: AsyncSession = Depends(get_db)):
    """템플릿 목록 페이지"""
    templates_list = await TemplateService.get_templates(db)
    return templates.TemplateResponse("templates.html", {
        "request": request,
        "templates": templates_list
    })


@app.get("/templates/create", response_class=HTMLResponse)
async def create_template_page(request: Request):
    """템플릿 생성 페이지"""
    return templates.TemplateResponse("create_template.html", {"request": request})


@app.get("/templates/{template_id}/edit", response_class=HTMLResponse)
async def edit_template_page(request: Request, template_id: int, db: AsyncSession = Depends(get_db)):
    """템플릿 수정 페이지"""
    template = await TemplateService.get_template_by_id(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="템플릿을 찾을 수 없습니다")

    return templates.TemplateResponse("edit_template.html", {
        "request": request,
        "template": template
    })


@app.get("/prompts/create", response_class=HTMLResponse)
async def create_prompt_page(request: Request, db: AsyncSession = Depends(get_db)):
    """프롬프트 생성 페이지 - 템플릿 선택"""
    templates_list = await TemplateService.get_templates(db)
    return templates.TemplateResponse("select_template.html", {
        "request": request,
        "templates": templates_list
    })


@app.get("/prompts/create/{template_id}", response_class=HTMLResponse)
async def create_prompt_form_page(request: Request, template_id: int, db: AsyncSession = Depends(get_db)):
    """프롬프트 생성 입력 폼 페이지"""
    template = await TemplateService.get_template_by_id(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="템플릿을 찾을 수 없습니다")

    return templates.TemplateResponse("create_prompt.html", {
        "request": request,
        "template": template
    })


@app.get("/prompts", response_class=HTMLResponse)
async def prompts_page(request: Request, db: AsyncSession = Depends(get_db)):
    """생성 내역 페이지"""
    prompts = await PromptService.get_prompts(db)

    # Gemini 응답 상태 정보 추가
    prompt_list = []
    for prompt in prompts:
        prompt_data = {
            "id": prompt.id,
            "title": prompt.title,
            "created_at": prompt.created_at,
            "has_gemini_response": prompt.gemini_response is not None,
            "gemini_status": prompt.gemini_response.status if prompt.gemini_response else None
        }
        prompt_list.append(prompt_data)

    return templates.TemplateResponse("prompts.html", {
        "request": request,
        "prompts": prompt_list
    })


@app.get("/prompts/{prompt_id}", response_class=HTMLResponse)
async def prompt_detail_page(request: Request, prompt_id: int, db: AsyncSession = Depends(get_db)):
    """프롬프트 상세 페이지"""
    prompt = await PromptService.get_prompt_by_id(db, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="프롬프트를 찾을 수 없습니다")

    return templates.TemplateResponse("prompt_detail.html", {
        "request": request,
        "prompt": prompt
    })


@app.get("/prompts/{prompt_id}/gemini", response_class=HTMLResponse)
async def gemini_response_page(request: Request, prompt_id: int, db: AsyncSession = Depends(get_db)):
    """Gemini 응답 페이지"""
    prompt = await PromptService.get_prompt_by_id(db, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="프롬프트를 찾을 수 없습니다")

    if not prompt.gemini_response:
        raise HTTPException(status_code=404, detail="Gemini 응답을 찾을 수 없습니다")

    return templates.TemplateResponse("gemini_response.html", {
        "request": request,
        "prompt": prompt,
        "gemini_response": prompt.gemini_response
    })


# API 엔드포인트
@app.post("/api/templates", response_model=TemplateResponse)
async def create_template_api(template_data: TemplateCreate, db: AsyncSession = Depends(get_db)):
    """템플릿 생성 API"""
    try:
        template = await TemplateService.create_template(db, template_data)
        return template
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/templates", response_model=List[TemplateListResponse])
async def get_templates_api(db: AsyncSession = Depends(get_db)):
    """템플릿 목록 조회 API"""
    templates_list = await TemplateService.get_templates(db)
    return templates_list


@app.get("/api/templates/{template_id}", response_model=TemplateResponse)
async def get_template_api(template_id: int, db: AsyncSession = Depends(get_db)):
    """템플릿 상세 조회 API"""
    template = await TemplateService.get_template_by_id(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="템플릿을 찾을 수 없습니다")
    return template


@app.put("/api/templates/{template_id}", response_model=TemplateResponse)
async def update_template_api(template_id: int, template_data: TemplateCreate, db: AsyncSession = Depends(get_db)):
    """템플릿 수정 API"""
    template = await TemplateService.update_template(db, template_id, template_data)
    if not template:
        raise HTTPException(status_code=404, detail="템플릿을 찾을 수 없습니다")
    return template


@app.delete("/api/templates/{template_id}")
async def delete_template_api(template_id: int, db: AsyncSession = Depends(get_db)):
    """템플릿 삭제 API"""
    success = await TemplateService.delete_template(db, template_id)
    if not success:
        raise HTTPException(status_code=404, detail="템플릿을 찾을 수 없습니다")
    return {"message": "템플릿이 삭제되었습니다"}


@app.post("/api/prompts", response_model=PromptResponse)
async def create_prompt_api(prompt_data: PromptCreate, db: AsyncSession = Depends(get_db)):
    """프롬프트 생성 API"""
    try:
        prompt = await PromptService.create_prompt(db, prompt_data)
        return prompt
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/prompts", response_model=List[PromptListResponse])
async def get_prompts_api(db: AsyncSession = Depends(get_db)):
    """프롬프트 목록 조회 API"""
    prompts = await PromptService.get_prompts(db)

    # Gemini 응답 상태 정보 추가
    prompt_list = []
    for prompt in prompts:
        prompt_data = {
            "id": prompt.id,
            "title": prompt.title,
            "created_at": prompt.created_at,
            "has_gemini_response": prompt.gemini_response is not None,
            "gemini_status": prompt.gemini_response.status if prompt.gemini_response else None
        }
        prompt_list.append(prompt_data)

    return prompt_list


@app.get("/api/prompts/{prompt_id}", response_model=PromptResponse)
async def get_prompt_api(prompt_id: int, db: AsyncSession = Depends(get_db)):
    """프롬프트 상세 조회 API"""
    prompt = await PromptService.get_prompt_by_id(db, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="프롬프트를 찾을 수 없습니다")
    return prompt


@app.delete("/api/prompts/{prompt_id}")
async def delete_prompt_api(prompt_id: int, db: AsyncSession = Depends(get_db)):
    """프롬프트 삭제 API"""
    success = await PromptService.delete_prompt(db, prompt_id)
    if not success:
        raise HTTPException(status_code=404, detail="프롬프트를 찾을 수 없습니다")
    return {"message": "프롬프트가 성공적으로 삭제되었습니다"}


async def process_gemini_request(prompt_id: int, prompt_content: str, db: AsyncSession):
    """백그라운드에서 Gemini API 호출 처리"""
    try:
        # Gemini 응답 레코드 생성
        gemini_response = await GeminiService.create_gemini_response(db, prompt_id)

        # Gemini API 호출
        response_content = await gemini_client.generate_content_async(prompt_content, os.getenv("GEMINI_MODEL"))

        # 응답 업데이트
        await GeminiService.update_gemini_response(
            db, gemini_response.id, response_content, "completed"
        )

    except Exception as e:
        # 에러 발생 시 상태 업데이트
        if 'gemini_response' in locals():
            await GeminiService.update_gemini_response(
                db, gemini_response.id, str(e), "error"
            )


@app.post("/api/prompts/{prompt_id}/gemini")
async def submit_to_gemini_api(prompt_id: int, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Gemini API로 프롬프트 제출"""
    prompt = await PromptService.get_prompt_by_id(db, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="프롬프트를 찾을 수 없습니다")

    # 백그라운드 태스크로 Gemini API 호출
    background_tasks.add_task(process_gemini_request, prompt_id, prompt.generated_content, db)

    return {"message": "Gemini API 요청이 시작되었습니다"}


@app.get("/api/prompts/{prompt_id}/gemini", response_model=GeminiResponseResponse)
async def get_gemini_response_api(prompt_id: int, db: AsyncSession = Depends(get_db)):
    """Gemini 응답 조회 API"""
    prompt = await PromptService.get_prompt_by_id(db, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="프롬프트를 찾을 수 없습니다")

    if not prompt.gemini_response:
        raise HTTPException(status_code=404, detail="Gemini 응답을 찾을 수 없습니다")

    return prompt.gemini_response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
