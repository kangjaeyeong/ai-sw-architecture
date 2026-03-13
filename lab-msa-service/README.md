# Lab: MSA AI 어시스턴트 서비스 분해 시연

## 시연 목표

LO8에서 설계한 사내 AI 어시스턴트의 5계층 서비스 분해도를 실제 동작하는 3개 마이크로서비스로 구현하여 시연합니다.

| 서비스 | 포트 | LO8 계층 | 역할 |
|--------|------|----------|------|
| 의도 분류 서비스 | 8001 | 도메인 서비스 | 질문을 HR/IT/재무로 라우팅 |
| RAG 검색 서비스 | 8002 | AI 인프라 | 도메인별 지식 베이스 검색 |
| 오케스트레이터 | 8000 | 게이트웨이 | 분류 → 검색 → LLM 응답 파이프라인 |

## 사전 준비

- Python 3.11 이상
- uv 패키지 매니저
- OpenAI API 키 (오케스트레이터의 LLM 응답 생성에 필요)

## 환경 설정

```bash
cd labs/lab-msa-service
uv sync
cp .env.example .env
# .env 파일에서 OPENAI_API_KEY를 실제 키로 변경
```

## 실행 방법

### 일괄 실행 (권장)

```bash
uv run python solution/run_all.py
```

3개 서비스가 하나의 프로세스에서 동시에 실행됩니다.

### 개별 실행

서비스를 각각 따로 띄우려면 3개 터미널에서 실행합니다.

```bash
uv run python solution/intent_service.py   # 포트 8001
uv run python solution/rag_service.py      # 포트 8002
uv run python solution/orchestrator.py     # 포트 8000
```

## 시연

### 데모 스크립트 실행

```bash
# 인터랙티브 모드 (직접 질문 입력)
uv run python solution/demo.py

# 데모 시나리오 4개 자동 실행
uv run python solution/demo.py --demo

# 단일 질문
uv run python solution/demo.py "재택근무 규정이 어떻게 되나요?"
```

인터랙티브 모드에서는 rich TUI 기반 대화형 인터페이스가 표시되며, 직접 질문을 입력할 수 있습니다. `demo`를 입력하면 데모 시나리오를 실행하고, `quit`으로 종료합니다.

### 개별 서비스 테스트

```bash
# 의도 분류 테스트
curl -X POST http://localhost:8001/classify \
  -H "Content-Type: application/json" \
  -d '{"message": "재택근무 규정이 어떻게 되나요?"}'

# RAG 검색 테스트
curl -X POST http://localhost:8002/search \
  -H "Content-Type: application/json" \
  -d '{"query": "재택근무", "domain": "hr", "top_k": 3}'

# 전체 파이프라인 테스트
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "VPN 접속하려면 어떻게 해야 하나요?"}'
```

### 헬스 체크

```bash
# 오케스트레이터 + 하위 서비스 상태 한 번에 확인
curl http://localhost:8000/health
```

### Swagger UI

각 서비스의 API 문서를 브라우저에서 확인할 수 있습니다.

- 의도 분류: http://localhost:8001/docs
- RAG 검색: http://localhost:8002/docs
- 오케스트레이터: http://localhost:8000/docs

## 아키텍처

```
사용자 질문
    │
    ▼
┌─────────────────────────────┐
│  오케스트레이터 (:8000)       │
│  (API Gateway 역할)          │
└──────┬──────────────┬───────┘
       │              │
       ▼              ▼
┌──────────────┐ ┌──────────────┐
│ 의도 분류     │ │ RAG 검색     │
│ (:8001)      │ │ (:8002)      │
│ HR/IT/재무    │ │ 도메인별 검색  │
└──────────────┘ └──────────────┘
                       │
              ┌────────┼────────┐
              ▼        ▼        ▼
          hr_kb    it_kb    finance_kb
```

## 파이프라인 흐름

1. 오케스트레이터가 사용자 질문을 수신합니다
2. 의도 분류 서비스에 질문을 전달하여 도메인(HR/IT/재무)을 판별합니다
3. 판별된 도메인으로 RAG 검색 서비스에 관련 문서를 요청합니다
4. 검색된 문서를 컨텍스트로 활용하여 LLM(gpt-5-mini)이 최종 응답을 생성합니다
5. 전체 파이프라인의 각 단계별 결과와 함께 응답을 반환합니다

## 핵심 포인트

1. **서비스 독립성**: 각 서비스는 독립적으로 배포, 스케일링, 장애 격리가 가능합니다
2. **도메인별 분리**: 의도 분류로 라우팅하여 불필요한 검색을 방지합니다
3. **파이프라인 투명성**: 응답에 각 단계의 결과가 포함되어 디버깅과 모니터링이 용이합니다
4. **GPU/CPU 분리 가능**: RAG 서비스(임베딩)는 GPU, 의도 분류(룰 기반)는 CPU로 분리 배포할 수 있습니다
