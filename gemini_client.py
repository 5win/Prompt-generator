import asyncio
import os
from typing import AsyncGenerator

from dotenv import load_dotenv
from google import genai

load_dotenv()


class GeminiClient:
    def __init__(self, api_key: str = None):
        if api_key is None:
            api_key = os.getenv("GEMINI_API_KEY")

        self.client = genai.Client(api_key=api_key)

    async def generate_content_async(self, prompt: str, model: str = None) -> str:
        """비동기로 Gemini API 호출"""
        try:
            # 동기 API를 비동기로 래핑
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                )
            )
            return response.text
        except Exception as e:
            raise Exception(f"Gemini API 호출 실패: {str(e)}")

    async def generate_content_stream_async(self, prompt: str, model: str = None) -> AsyncGenerator[
        str, None]:
        """스트리밍 방식으로 Gemini API 호출"""
        try:
            loop = asyncio.get_event_loop()
            response_stream = await loop.run_in_executor(
                None,
                lambda: self.client.models.generate_content_stream(
                    model=model,
                    contents=prompt
                )
            )

            for chunk in response_stream:
                yield chunk.text

        except Exception as e:
            raise Exception(f"Gemini API 스트림 호출 실패: {str(e)}")


# 전역 클라이언트 인스턴스
gemini_client = GeminiClient()
