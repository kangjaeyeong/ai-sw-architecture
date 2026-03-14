"""
오케스트레이터 서비스 (Orchestrator / API Gateway)

클라이언트 요청을 받아 의도 분류 → RAG 검색 → LLM 응답 생성 파이프라인을 실행합니다.
LO8 서비스 분해도의 '게이트웨이 계층'에 해당합니다.

흐름:
  1. 사용자 질문 수신
  2. 의도 분류 서비스 호출 → 도메인 판별
  3. RAG 검색 서비스 호출 → 관련 문서 검색
  4. LLM으로 최종 응답 생성 (검색 결과를 컨텍스트로 활용)

포트: 8000
"""

import asyncio
import os

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="AI 어시스턴트 오케스트레이터", version="0.1.0")

# 마이크로서비스 엔드포인트
INTENT_SERVICE_URL = os.getenv("INTENT_SERVICE_URL", "http://localhost:8001")
RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://localhost:8002")

# OpenAI 클라이언트
client = OpenAI()

SYSTEM_PROMPT = """당신은 사내 AI 어시스턴트입니다.
제공된 사내 문서를 기반으로 직원의 질문에 정확하게 답변합니다.
문서에 없는 내용은 추측하지 말고, 해당 부서에 문의하도록 안내하십시오.
답변은 간결하고 격식체(합쇼체)로 작성합니다."""


class ChatRequest(BaseModel):
    message: str
    context: list[str] = []


class PipelineStep(BaseModel):
    step: str
    service: str
    result: dict


class ChatResponse(BaseModel):
    answer: str
    domain: str
    confidence: float
    pipeline: list[PipelineStep]
    sources: list[str]


async def call_intent_service(message: str) -> dict:
    """의도 분류 서비스를 호출합니다."""
    async with httpx.AsyncClient(timeout=10.0) as http:
        response = await http.post(
            f"{INTENT_SERVICE_URL}/classify",
            json={"message": message},
        )
        response.raise_for_status()
        return response.json()


async def call_rag_service(query: str, domain: str) -> dict:
    """RAG 검색 서비스를 호출합니다."""
    async with httpx.AsyncClient(timeout=10.0) as http:
        response = await http.post(
            f"{RAG_SERVICE_URL}/search",
            json={"query": query, "domain": domain, "top_k": 3},
        )
        response.raise_for_status()
        return response.json()


def generate_answer(message: str, context_docs: list[dict]) -> str:
    """검색된 문서를 컨텍스트로 활용하여 LLM 응답을 생성합니다."""
    if not context_docs:
        return "관련 문서를 찾을 수 없습니다. 해당 부서에 직접 문의하시기 바랍니다."

    # 검색 결과를 프롬프트 컨텍스트로 구성
    context_text = "\n\n".join(
        f"[{doc['id']}] {doc['title']}\n{doc['content']}"
        for doc in context_docs
    )

    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"사내 문서:\n{context_text}\n\n질문: {message}",
            },
        ],
        max_completion_tokens=16384,
    )
    return response.choices[0].message.content or "응답을 생성할 수 없습니다."


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """사용자 질문에 대한 전체 파이프라인을 실행합니다."""
    pipeline: list[PipelineStep] = []

    # Step 1: 의도 분류
    intent_result = await call_intent_service(request.message)
    pipeline.append(PipelineStep(
        step="의도 분류",
        service=f"{INTENT_SERVICE_URL}/classify",
        result=intent_result,
    ))

    domain = intent_result["domain"]
    confidence = intent_result["confidence"]

    # Step 2: RAG 검색
    rag_result = await call_rag_service(request.message, domain)
    pipeline.append(PipelineStep(
        step="RAG 검색",
        service=f"{RAG_SERVICE_URL}/search",
        result=rag_result,
    ))

    context_docs = rag_result.get("results", [])
    sources = [doc["source"] for doc in context_docs]

    # Step 3: LLM 응답 생성 (동기 OpenAI 호출을 별도 스레드에서 실행)
    answer = await asyncio.to_thread(generate_answer, request.message, context_docs)
    pipeline.append(PipelineStep(
        step="LLM 응답 생성",
        service="OpenAI gpt-5-mini",
        result={"tokens_used": len(answer)},
    ))

    return ChatResponse(
        answer=answer,
        domain=domain,
        confidence=confidence,
        pipeline=pipeline,
        sources=sources,
    )


@app.get("/health")
async def health():
    """오케스트레이터 및 하위 서비스 상태를 확인합니다."""
    services = {}
    for name, url in [("intent", INTENT_SERVICE_URL), ("rag", RAG_SERVICE_URL)]:
        try:
            async with httpx.AsyncClient(timeout=3.0) as http:
                resp = await http.get(f"{url}/health")
                services[name] = resp.json()
        except Exception as e:
            services[name] = {"status": "unreachable", "error": str(e)}

    return {
        "status": "healthy",
        "service": "orchestrator",
        "downstream": services,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
