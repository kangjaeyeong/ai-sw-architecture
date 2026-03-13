# Lab 2: A2A 프로토콜 기반 아키텍처 심의위원회 (ARB)

## 실습 목표

단일 AI 에이전트는 하나의 관점에 편향된 분석을 제공합니다.
실제 아키텍처 심의에서는 보안, 성능, 비용, 운영 등 **서로 다른 우선순위를 가진 전문가들이 의견을 교환**하며 균형 잡힌 결론을 도출합니다.

이 실습에서는 A2A(Agent-to-Agent) 프로토콜을 사용하여 4명의 전문가 에이전트가 설계 제안서를 리뷰하고, 오케스트레이터가 **상충하는 의견을 종합**하여 최종 심의 결과를 도출하는 시스템을 구현합니다.

### 학습 포인트

- A2A 프로토콜의 핵심 개념: AgentCard, Task, Message, Artifact
- 멀티에이전트 시스템에서의 관점 충돌과 해결
- 오케스트레이터 패턴을 통한 에이전트 협업
- LLM 기반 분석과 규칙 기반 폴백의 하이브리드 구조
- 전통적 REST API 방식과 A2A 프로토콜의 구조적 차이

---

## A2A 프로토콜 핵심 개념

A2A(Agent-to-Agent)는 Google이 2025년 4월에 공개한 에이전트 간 통신 표준 프로토콜입니다.
에이전트들이 서로를 발견하고, 메시지를 주고받으며, 작업을 위임할 수 있게 합니다.

### 4가지 핵심 구성 요소

| 구성 요소 | 역할 | 이 실습에서의 적용 |
|-----------|------|-------------------|
| **AgentCard** | 에이전트가 자신의 이름, 능력, URL을 공개하는 메타데이터. 다른 에이전트가 이를 읽고 적절한 에이전트를 찾을 수 있습니다. | 보안/성능/비용/운영 에이전트가 각자의 AgentCard를 등록합니다. 오케스트레이터는 AgentCard를 통해 에이전트를 탐색합니다. |
| **Message** | 에이전트 간 통신의 기본 단위. 역할(USER/AGENT)과 내용(TextContent 등)으로 구성됩니다. 모든 에이전트가 **동일한 형식**으로 메시지를 주고받습니다. | 오케스트레이터가 설계안을 Message로 전송하고, 에이전트가 리뷰 결과를 Message로 반환합니다. |
| **Task** | 에이전트에게 요청한 작업의 상태를 추적합니다. submitted, working, completed, failed 등의 상태를 가집니다. | 각 에이전트에 대한 리뷰 요청이 하나의 Task입니다. |
| **Artifact** | Task 수행 결과물. 텍스트, 이미지, 파일 등 다양한 형태의 산출물을 포함할 수 있습니다. | 각 에이전트의 리뷰 보고서(JSON)가 Artifact입니다. |

### A2A 통신 흐름

```
1. 에이전트 등록
   SecurityAgent → AgentCard(name="보안 리뷰", url=":5001", skills=["보안 분석"])
   PerformanceAgent → AgentCard(name="성능 리뷰", url=":5002", skills=["성능 분석"])

2. 에이전트 탐색 (Discovery)
   오케스트레이터가 AgentCard를 읽어 어떤 에이전트가 있는지 파악

3. 메시지 교환
   오케스트레이터 → Message(role=USER, content="설계안 JSON")
   에이전트     → Message(role=AGENT, content="리뷰 결과 JSON")

4. 결과 종합
   오케스트레이터가 모든 에이전트의 응답을 취합하여 최종 보고서 생성
```

---

## 전통적 REST API vs A2A 프로토콜 비교

전통적 REST API로 동일한 멀티에이전트 시스템을 구현하면 어떤 문제가 발생하는지 비교합니다.
`solution/traditional_multi_service.py`에서 실제 코드를 확인할 수 있습니다.

### 구조 비교

| 항목 | 전통적 REST API | A2A 프로토콜 |
|------|----------------|-------------|
| **엔드포인트** | 서비스마다 개별 정의 (`/api/v1/security/review`, `/api/v1/ops/readiness`) | 모든 에이전트 동일 (`/message`) |
| **요청 형식** | 서비스마다 다름 (`{"proposal": ...}`, `{"system_spec": ...}`) | 표준화된 Message 객체 |
| **응답 형식** | 서비스마다 다름 (`issues`, `findings`, `analysis`, `gaps`) | 표준화된 Message 객체 |
| **응답 변환** | 서비스별 변환 코드 필요 (`normalize_response()`) | 불필요 |
| **서비스 탐색** | URL/스펙을 하드코딩 | AgentCard 기반 자동 탐색 |
| **새 서비스 추가** | 엔드포인트, 요청 형식, 변환 코드 모두 수정 | AgentCard 등록만으로 추가 |
| **대화 상태** | 직접 구현 필요 | 프로토콜 내장 (Task, Conversation) |
| **에이전트 간 통신** | 개별 API 호출 코드 작성 | 표준 프로토콜로 통일 |

### 코드 비교 예시

**REST API 방식 (서비스마다 다른 호출 코드)**
```python
# 보안 서비스 호출
resp1 = requests.post("http://localhost:6001/api/v1/security/review",
                       json={"proposal": proposal})
# 성능 서비스 호출 (다른 URL, 다른 키)
resp2 = requests.post("http://localhost:6002/api/v1/performance/analyze",
                       json={"system_spec": proposal})
# 응답 형식도 다름: resp1은 "issues", resp2는 "findings"
```

**A2A 프로토콜 방식 (동일한 호출 코드)**
```python
# 모든 에이전트에 동일한 코드
for agent_url in ["http://localhost:5001", "http://localhost:5002"]:
    client = A2AClient(agent_url)
    message = Message(role=MessageRole.USER, content=TextContent(text=proposal_json))
    response = client.send_message(message)  # 동일한 응답 형식
```

### 비교 데모 실행

```bash
# 서버 없이 코드 구조 차이를 확인하는 데모
uv run python solution/traditional_multi_service.py
```

---

## 아키텍처 구조

```
                    설계 제안서
                        |
                        v
              +-------------------+
              |   오케스트레이터   |
              | (orchestrator.py) |
              +-------------------+
               /    |    |    \
              v     v    v     v
         +------+ +------+ +------+ +------+
         | 보안 | | 성능 | | 비용 | | 운영 |
         | :5001| | :5002| | :5003| | :5004|
         +------+ +------+ +------+ +------+
              \    |    |    /
               v   v    v  v
        +-----------------------------+
        |  관점 충돌 분석 및 종합 보고서  |
        +-----------------------------+
```

- 각 에이전트는 독립된 A2A 서버로 실행됩니다 (port 5001 ~ 5004).
- 오케스트레이터는 에이전트 목록을 하드코딩하지 않고 **포트 범위를 스캔하여 AgentCard로 자동 발견**합니다.
- 발견된 에이전트에게 **병렬로** 리뷰를 요청하고, 관점 충돌을 분석하여 최종 판정을 내립니다.

### 왜 A2A 프로토콜인가? (Tool Calling / 서브에이전트와 비교)

"LLM Tool Calling으로 4개 함수를 호출하면 더 간단하지 않나?"라는 의문이 들 수 있습니다.
핵심 차이는 **에이전트의 독립성과 발견 가능성**입니다.

| 비교 항목 | Tool Calling | 단일 프로세스 서브에이전트 | A2A 프로토콜 |
|-----------|-------------|------------------------|-------------|
| **새 관점 추가** | 코드 수정, 재배포 필요 | 코드 수정, 재시작 필요 | 새 포트에서 서버 실행만 하면 자동 발견 |
| **독립 배포** | 불가 (한 프로세스) | 불가 (한 프로세스) | 에이전트별 독립 배포, 스케일링 |
| **다른 팀/조직** | 불가 | 불가 | 보안팀이 보안 에이전트를, 비용팀이 비용 에이전트를 각자 운영 |
| **이기종 언어** | LLM이 지원하는 도구만 | 같은 언어/프레임워크 | Python, Node.js, Go 등 자유 |
| **장애 격리** | 하나 실패하면 전체 영향 | 하나 실패하면 전체 영향 | 나머지 에이전트는 정상 응답 |

이 실습에서 체험할 수 있는 A2A의 핵심:

```bash
# 1. 기본 4개 에이전트로 심의
uv run python solution/orchestrator.py

# 2. 법무 에이전트를 5005번 포트에 추가 실행 (코드 변경 없이)
# 3. 오케스트레이터가 자동 발견하여 5명의 전문가가 심의
uv run python solution/orchestrator.py --ports 5001-5005
```

### 에이전트 분석 모드

각 에이전트는 **하이브리드 분석 구조**를 채택하고 있습니다.

| 모드 | 조건 | 특징 |
|------|------|------|
| **LLM 기반** | `OPENAI_API_KEY` 환경 변수가 설정된 경우 | 에이전트별 시스템 프롬프트로 LLM에게 분석을 요청합니다. 다양한 제안서에 유연하게 대응할 수 있습니다. |
| **규칙 기반** | API 키가 없는 경우 (기본값) | 제안서의 특정 키 존재 여부로 판정합니다. API 키 없이도 즉시 실행 가능합니다. |
| **자동 폴백** | LLM 호출 실패 시 | LLM 모드에서 오류가 발생하면 규칙 기반으로 자동 전환됩니다. |

### 데모 시나리오: 반려에서 승인까지

이 실습에는 2개의 설계 제안서가 포함되어 있습니다.

| 제안서 | 파일 | 결과 | 설명 |
|--------|------|------|------|
| **v1 (원안)** | `design_proposal.json` | **반려** | 보안 대책, 비용 분석, 운영 교육 계획이 부재합니다. |
| **v2 (수정안)** | `design_proposal_v2.json` | **승인** | v1의 지적 사항을 모두 반영하여 보안, 비용, 운영 계획을 보강하였습니다. |

v1에서 반려를 받은 후 v2를 수정하여 승인을 받는 **현실적인 심의 사이클**을 체험할 수 있습니다.

---

## 사전 준비

### 1. 의존성 설치

```bash
cd labs/lab-a2a-agents
uv sync
```

### 2. 환경 변수 설정 (선택)

규칙 기반 분석이 기본이므로 API 키 없이도 실행할 수 있습니다.

```bash
cp .env.example .env
# LLM 모드를 사용하려면 OPENAI_API_KEY를 설정하십시오.
```

---

## 실습 순서 (25분)

### Step 1: 설계 제안서 확인 (2분)

`data/design_proposal.json` 파일을 열어 제안 내용을 확인하십시오.

```bash
cat data/design_proposal.json | python -m json.tool
```

핵심 확인 사항:
- **현재 시스템**: Java 8, Oracle DB, WebLogic 기반 온프레미스
- **전환 대상**: AWS EKS 기반 컨테이너 아키텍처
- **예산/기간**: 12억원 / 18개월
- **기대 효과**: 장애 복구 4시간에서 15분으로 단축, 운영 인력 60% 감축

### Step 2: 전문가 에이전트 구현 (10분)

`starter/agents.py` 파일을 열어 4개 에이전트의 분석 로직을 구현하십시오.

각 에이전트의 `handle_message` 메서드에서 TODO 주석을 따라 분석을 추가합니다.

```python
# 예시: SecurityReviewAgent의 데이터 주권 분석
if proposal.get("proposed_changes", {}).get("target_cloud") == "AWS":
    findings.append({
        "category": "데이터 주권",
        "severity": "높음",
        "finding": "퍼블릭 클라우드 전환 시 개인정보보호법에 따른 ...",
        "recommendation": "데이터 분류 체계를 수립하고 ...",
    })
```

**핵심 포인트**: 각 에이전트가 **서로 다른 관점**에서 분석하도록 구현하십시오.
- 성능 에이전트는 오토스케일링을 긍정적으로 평가
- 비용 에이전트는 TCO 증가를 우려
- 보안 에이전트는 고급 보안 체계를 요구
- 운영 에이전트는 팀 역량 부족을 지적

### Step 3: 에이전트 서버 실행 (2분)

터미널 1에서 에이전트를 실행합니다.

```bash
# starter 코드 실행
uv run python starter/agents.py

# 또는 완성된 solution 코드 실행
uv run python solution/agents_server.py
```

실행하면 4개의 에이전트가 각각 port 5001 ~ 5004에서 시작됩니다.

```
╭──────────────────────────────────────────────────────────╮
│  아키텍처 심의위원회(ARB) — 전문가 에이전트                  │
│  분석 모드: 규칙 기반                                      │
╰──────────────────────────────────────────────────────────╯

        에이전트 목록
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 에이전트                    ┃ 포트 ┃ URL                       ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Security Review Agent      │ 5001 │ http://localhost:5001     │
│ Performance Review Agent   │ 5002 │ http://localhost:5002     │
│ Cost Review Agent          │ 5003 │ http://localhost:5003     │
│ Ops Review Agent           │ 5004 │ http://localhost:5004     │
└────────────────────────────┴──────┴──────────────────────────┘

╭──────────────────────────────────────────────────────────╮
│  모든 에이전트가 실행 중입니다. Ctrl+C로 종료하십시오.       │
╰──────────────────────────────────────────────────────────╯
```

### Step 4: v1 설계안 심의 실행 (5분)

터미널 2를 열어 오케스트레이터를 실행합니다.

```bash
# v1 설계안 심의 (기본값)
uv run python solution/orchestrator.py
```

**예상 결과**: 보안과 운영 에이전트가 **반려** 판정을 내리며 최종 **반려**가 됩니다.

### Step 5: v2 수정안으로 재심의 (3분)

v1에서 지적된 사항을 반영한 수정안(v2)으로 다시 심의합니다.

```bash
# v2 설계안 심의
uv run python solution/orchestrator.py --proposal design_proposal_v2.json
```

**예상 결과**: 모든 에이전트가 **승인** 판정을 내리며 최종 **승인**이 됩니다.

### Step 6: 결과 비교 및 토론 (3분)

v1과 v2의 심의 결과를 비교하고 다음 질문에 대해 토론합니다:
- v2에서 어떤 항목들이 개선되었습니까?
- 에이전트 간 관점 충돌은 어떻게 해소되었습니까?
- LLM 기반과 규칙 기반 분석의 장단점은 무엇입니까?

---

## 실행 결과 예시

### v1 설계안 (반려)

```
╭──────────────────────────────────────────────────────────╮
│  아키텍처 심의위원회(ARB) 종합 보고서                       │
╰──────────────────────────────────────────────────────────╯

           전문가별 판정
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 에이전트         ┃ 판정       ┃ 요약                       ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 보안 리뷰        │ 반려       │ 데이터 주권, 암호화 미비    │
│ 성능 리뷰        │ 조건부 승인 │ 스케일링 긍정, SLA 미정    │
│ 비용 리뷰        │ 조건부 승인 │ 3년 TCO 증가 우려          │
│ 운영 리뷰        │ 반려       │ 클라우드 역량 부재          │
└─────────────────┴────────────┴───────────────────────────┘

╭──────────────────────────────────────────────────────────╮
│  최종 판정: 반려                                          │
╰──────────────────────────────────────────────────────────╯
```

### v2 수정안 (승인)

```
           전문가별 판정
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 에이전트         ┃ 판정   ┃ 요약                          ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 보안 리뷰        │ 승인   │ KMS, PSS 적용 확인            │
│ 성능 리뷰        │ 승인   │ SLA 명시, 캐싱 전략 포함       │
│ 비용 리뷰        │ 승인   │ RI/Spot 전략 반영              │
│ 운영 리뷰        │ 승인   │ 교육 계획 및 인력 재배치 확인   │
└─────────────────┴────────┴──────────────────────────────┘

  총 발견 사항: 16건 (높음: 0건, 중간: 5건, 낮음: 11건)
  관점 충돌: 0건

╭──────────────────────────────────────────────────────────╮
│  최종 판정: 승인                                          │
╰──────────────────────────────────────────────────────────╯
```

---

## 평가 (Evaluation)

멀티에이전트 시스템은 개별 에이전트의 응답 품질뿐 아니라, 에이전트 간 상호작용까지 검증해야 합니다.

`solution/eval.py`는 3가지 평가 패턴을 실제로 구현합니다.

### 실행 방법

에이전트 서버가 실행 중인 상태에서 별도 터미널에서 실행합니다.

```bash
# 터미널 1: 에이전트 실행 (이미 실행 중이면 생략)
uv run python solution/agents_server.py

# 터미널 2: 평가 실행
uv run python solution/eval.py
```

### 3가지 평가 패턴

| 패턴 | 검증 대상 | 사례 |
|------|----------|------|
| 1. 에이전트별 응답 평가 | 각 에이전트가 올바른 분석 결과를 반환하는지 | 보안 에이전트가 데이터 주권/암호화를 분석하는지, 운영 에이전트가 역량 부재를 지적하는지 |
| 2. 의사결정 일관성 평가 | 판정(verdict) 로직이 규칙에 부합하는지 | 높은 심각도 2건 이상이면 반려, high_severity_count가 정확한지 |
| 3. 에이전트 간 충돌 탐지 | 상충하는 관점이 올바르게 식별되는지 | 성능 대 비용 충돌, 보안 요구 대 운영 역량 충돌이 감지되는지 |

---

## A2A 프로토콜 구성 요소와 코드 매핑

이 실습의 코드가 A2A 프로토콜의 각 구성 요소를 어떻게 사용하는지 정리합니다.

### AgentCard — 에이전트 자기 설명

```python
# agents_server.py에서 에이전트를 등록할 때 AgentCard를 생성합니다.
card = AgentCard(
    name="Security Review Agent",           # 에이전트 이름
    description="보안 관점에서 아키텍처를 리뷰합니다",  # 능력 설명
    url="http://localhost:5001",            # 접근 URL
    version="1.0.0",                        # 버전
    capabilities={                          # 지원 기능
        "pushNotifications": False,
        "stateTransitionHistory": False,
    },
)
```

### BaseReviewAgent — 하이브리드 분석 베이스 클래스

```python
# agents/base.py — LLM과 규칙 기반을 모두 지원하는 공통 베이스 클래스
class BaseReviewAgent(A2AServer):
    agent_name: str = ""
    system_prompt: str = ""
    model: str = "gpt-5-mini"

    def __init__(self, agent_card):
        super().__init__(agent_card)
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self._openai = OpenAI(api_key=api_key)
            self._use_llm = True    # LLM 모드
        else:
            self._use_llm = False   # 규칙 기반 모드

    def handle_message(self, message):
        if self._use_llm:
            result = self._analyze_with_llm(proposal_text)
        else:
            result = self.analyze_rule_based(proposal)
        return Message(role=MessageRole.AGENT, content=TextContent(text=json.dumps(result)))
```

### A2AClient — 에이전트 호출

```python
# 오케스트레이터에서 에이전트를 호출합니다.
client = A2AClient("http://localhost:5001")
message = Message(
    role=MessageRole.USER,
    content=TextContent(text=proposal_json),
)
response = client.send_message(message)  # 표준화된 응답
```

---

## 관점 충돌이 가치 있는 이유

단일 에이전트는 하나의 최적화 목표만 추구합니다.
멀티에이전트 시스템에서 관점 충돌이 발생하면, 오케스트레이터가 **트레이드오프를 명시적으로 드러내고** 균형 잡힌 의사결정을 지원할 수 있습니다.

이 패턴은 실제 기업의 아키텍처 심의위원회, 투자 심의, 리스크 평가 등에 적용할 수 있습니다.

---

## 파일 구조

```
lab-a2a-agents/
├── README.md                              ← 이 문서
├── pyproject.toml                         ← 의존성 정의
├── .env.example                           ← 환경 변수 템플릿
├── data/
│   ├── design_proposal.json               ← v1 설계 제안서 (반려 예상)
│   └── design_proposal_v2.json            ← v2 수정 제안서 (승인 예상)
├── solution/
│   ├── agents_server.py                   ← 에이전트 4종 일괄 실행 서버
│   ├── agents/                            ← 에이전트 모듈 패키지
│   │   ├── __init__.py                    ← 에이전트 클래스 export
│   │   ├── base.py                        ← BaseReviewAgent (LLM/규칙 하이브리드)
│   │   ├── security.py                    ← 보안 리뷰 에이전트
│   │   ├── performance.py                 ← 성능 리뷰 에이전트
│   │   ├── cost.py                        ← 비용 리뷰 에이전트
│   │   └── ops.py                         ← 운영 리뷰 에이전트
│   ├── orchestrator.py                    ← 오케스트레이터 (완성본)
│   ├── eval.py                            ← 멀티에이전트 평가 스크립트
│   └── traditional_multi_service.py       ← REST API 비교 예제
└── starter/
    ├── agents.py                          ← 에이전트 (TODO 포함, 실습용)
    └── orchestrator.py                    ← 오케스트레이터 (TODO 포함, 실습용)
```

---

## 강사 데모 시나리오

### 데모 1: v1 반려 — 동적 에이전트 발견 (5분)

```bash
# 터미널 1: 에이전트 서버 시작
uv run python solution/agents_server.py

# 터미널 2: v1 심의 실행 (에이전트 자동 발견)
uv run python solution/orchestrator.py
```

**포인트**: 오케스트레이터가 에이전트를 자동 발견하는 과정을 보여줍니다. "에이전트 탐색" 단계에서 4개 에이전트의 이름과 설명이 AgentCard로부터 출력됩니다. 보안과 운영에서 반려, 3건의 관점 충돌 발생.

### 데모 2: v2 승인 (3분)

```bash
# 터미널 2: v2 심의 실행
uv run python solution/orchestrator.py --proposal design_proposal_v2.json
```

**포인트**: v1의 지적 사항을 모두 반영하여 전원 승인. 실제 심의 사이클 체험.

### 데모 3: LLM 모드 (선택, 3분)

```bash
# .env에 OPENAI_API_KEY 설정 후 에이전트 재시작
uv run python solution/agents_server.py
# "분석 모드: LLM"이 표시됨

# 동일한 오케스트레이터 실행 (LLM 모드에서는 병렬 요청이므로 약 30초)
uv run python solution/orchestrator.py
```

**포인트**: 규칙 기반과 달리 LLM이 제안서를 자유롭게 분석. 다양한 제안서에 유연하게 대응.

### 데모 4: 에이전트 동적 추가 (A2A 핵심 체험, 3분)

```bash
# 터미널 3: 법무 에이전트를 5005번 포트에 추가 실행
# (agents_server.py 수정 없이, 별도 스크립트로 실행 가능)

# 터미널 2: 탐색 범위를 넓혀서 다시 심의
uv run python solution/orchestrator.py --ports 5001-5005
```

**포인트**: 오케스트레이터 코드를 한 줄도 수정하지 않고 새 에이전트가 심의에 참여합니다. 이것이 Tool Calling이나 서브에이전트 방식과의 핵심 차이점입니다.

---

## 확장 아이디어

- 에이전트 간 토론(Debate) 라운드를 추가하여 합의를 도출
- 새로운 전문가 에이전트(법무, 데이터, UX 등)를 추가하여 심의 범위를 확장
- A2A AgentCard의 skills 필드를 활용하여 에이전트 능력 기반 라우팅 구현
