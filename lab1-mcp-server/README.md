# Lab 1: FastMCP HR 도구 서버 구축

## 실습 목표

사내 AI 어시스턴트가 HR 시스템에 접근할 수 있도록 MCP(Model Context Protocol) 서버를 구축합니다. 이 실습을 통해 다음을 학습합니다.

- MCP 프로토콜의 도구(Tool) 개념을 이해합니다
- FastMCP 라이브러리로 도구 서버를 구현합니다
- OpenAI function calling으로 MCP 도구를 AI에 연결합니다
- 전통적 REST API와 MCP 방식의 차이점을 비교합니다

**소요 시간**: 약 25분

## 시나리오

회사에서 AI 어시스턴트를 도입하려고 합니다. 이 어시스턴트가 HR 관련 질문에 답변하려면 사내 시스템에 접근해야 합니다. MCP 서버를 통해 다음 3가지 도구를 제공합니다.

| 도구 | 기능 |
|------|------|
| `search_hr_policy` | 사내 규정을 키워드로 검색합니다 |
| `get_leave_balance` | 직원의 연차 잔여일을 조회합니다 |
| `lookup_org_chart` | 부서별 조직도를 조회합니다 |

## 사전 준비

- Python 3.11 이상
- uv 패키지 매니저 ([설치 안내](https://docs.astral.sh/uv/getting-started/installation/))
- OpenAI API 키 (클라이언트 실행 시 필요)

uv가 설치되어 있지 않은 경우 아래 명령어로 설치하십시오.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 환경 설정

1. 실습 디렉터리로 이동합니다.

```bash
cd labs/lab1-mcp-server
```

2. 의존성을 설치합니다.

```bash
uv sync
```

3. 환경변수를 설정합니다. (클라이언트 사용 시 필요)

```bash
cp .env.example .env
# .env 파일을 열어서 OPENAI_API_KEY를 실제 키로 변경하십시오
```

## 실습 진행 순서

### Step 1: 데이터 파일 확인

`data/` 폴더에 있는 3개의 JSON 파일을 열어 구조를 파악하십시오.

- `hr_policies.json`: 사내 규정 목록 (id, title, category, content)
- `employees.json`: 직원 정보와 연차 현황 (employee_id, name, remaining_leave 등)
- `org_chart.json`: 부서별 조직도 (부서명을 키로, 팀장과 팀원 정보)

### Step 2: 스타터 코드 열기

`starter/server.py` 파일을 열어 전체 구조를 확인하십시오. `load_json()` 유틸리티 함수는 이미 구현되어 있습니다. 3개의 도구 함수 본문에 있는 TODO 부분을 채워야 합니다.

### Step 3: search_hr_policy 구현

규정 데이터를 불러와서 키워드 매칭으로 검색하는 로직을 구현합니다.

- `load_json("hr_policies.json")`으로 데이터를 불러옵니다
- 각 규정의 title, category, content를 합쳐서 query 키워드가 포함되는지 확인합니다
- 매칭되는 규정이 있으면 제목과 내용을 문자열로 반환합니다
- 매칭되는 규정이 없으면 안내 메시지를 반환합니다

### Step 4: get_leave_balance 구현

직원 데이터에서 사번으로 검색하여 연차 정보를 반환하는 로직을 구현합니다.

- `load_json("employees.json")`으로 데이터를 불러옵니다
- employee_id가 일치하는 직원을 찾아 연차 정보를 딕셔너리로 반환합니다
- 해당 직원이 없으면 error 키가 포함된 딕셔너리를 반환합니다

### Step 5: lookup_org_chart 구현

조직도 데이터에서 부서명으로 조직 정보를 반환하는 로직을 구현합니다.

- `load_json("org_chart.json")`으로 데이터를 불러옵니다
- department를 키로 해당 부서 정보를 조회합니다
- 부서를 찾지 못하면 사용 가능한 부서 목록을 안내합니다

### Step 6: 서버 실행 및 Inspector 테스트

작성을 완료한 후 아래 단계를 따라 테스트합니다.

### Step 7: AI 클라이언트 연동

서버가 정상 동작하면, 클라이언트로 AI 연동을 확인합니다. `starter/client.py`의 TODO를 완성하십시오.

- `mcp_tools_to_openai_tools()`: MCP 도구 스키마를 OpenAI tools 형식으로 변환
- `chat_loop()`: OpenAI API 호출과 도구 호출 결과 처리

## 실행 및 테스트 방법

### 1. MCP 서버 실행

스타터 코드를 완성했다면, 아래 명령어로 MCP 서버를 실행합니다.

```bash
# starter 코드를 완성한 경우
uv run python starter/server.py

# 또는 solution 코드로 바로 확인하는 경우
uv run python solution/server.py
```

서버가 정상 실행되면 stdio 모드로 MCP 요청을 대기합니다.

### 2. MCP Inspector로 테스트

FastMCP에 내장된 Inspector를 사용하여 브라우저에서 테스트할 수 있습니다.

```bash
uv run fastmcp dev inspector solution/server.py
```

Inspector가 실행되면 브라우저에서 다음을 시도하십시오.

1. Tools 탭에서 등록된 3개 도구를 확인합니다
2. `search_hr_policy`에 "연차"를 입력하여 검색 결과를 확인합니다
3. `get_leave_balance`에 "EMP-001"을 입력하여 연차 잔여일을 확인합니다
4. `lookup_org_chart`에 "개발팀"을 입력하여 조직도를 확인합니다

### 3. AI 클라이언트 실행

`.env` 파일에 OpenAI API 키를 설정한 후, 클라이언트를 실행합니다.

```bash
# solution 코드 실행
uv run python solution/client.py

# 또는 starter 코드를 완성한 경우
uv run python starter/client.py
```

클라이언트가 실행되면 자연어로 질문할 수 있습니다.

```
질문> 김민수 연차 며칠 남았어?
  [도구 호출] get_leave_balance({"employee_id": "EMP-001"})

답변> 김민수님의 연차 현황입니다. 총 17일 중 8일을 사용하여 9일이 남아있습니다.

질문> 재택근무 규정 알려줘
  [도구 호출] search_hr_policy({"query": "재택근무"})

답변> 재택근무는 주 2회까지 신청 가능하며, 팀장 사전 승인이 필요합니다...
```

### 4. REST API 비교 실행

전통적 REST API 서버를 실행하여 MCP 방식과 비교합니다.

```bash
uv run python solution/traditional_api.py
```

서버가 실행되면 아래 URL로 접속할 수 있습니다.

- Swagger UI: http://localhost:8000/docs
- 규정 검색: http://localhost:8000/api/hr-policies?q=연차
- 연차 조회: http://localhost:8000/api/employees/EMP-001/leave
- 조직도: http://localhost:8000/api/org-chart/개발팀

### Claude Desktop에서 연동 (선택 사항)

Claude Desktop의 `claude_desktop_config.json`에 아래 설정을 추가하면 Claude와 직접 연동할 수 있습니다.

```json
{
  "mcpServers": {
    "hr-tools": {
      "command": "uv",
      "args": ["run", "python", "solution/server.py"],
      "cwd": "/path/to/lab1-mcp-server"
    }
  }
}
```

## 전통적 REST API와 MCP 비교

### 코드 수준 비교

| 관점 | REST API (`traditional_api.py`) | MCP 서버 (`server.py`) |
|------|------|------|
| 프레임워크 | FastAPI (HTTP 서버) | FastMCP (MCP 프로토콜) |
| 인터페이스 정의 | URL 경로, HTTP 메서드, 쿼리 파라미터 | 함수 이름, 파라미터, docstring |
| API 문서 | OpenAPI/Swagger 자동 생성 | MCP 도구 스키마 자동 생성 |
| 호출 방식 | HTTP 요청 (GET, POST 등) | MCP 프로토콜 (JSON-RPC) |
| 클라이언트 | REST 클라이언트 (curl, fetch 등) | MCP 클라이언트 (Claude, 커스텀) |
| 에러 처리 | HTTP 상태 코드 (404, 500 등) | 구조화된 응답 (error 키) |

### 아키텍처 수준 비교

| 관점 | REST API | MCP |
|------|------|------|
| 설계 목적 | 사람 또는 프로그램이 호출 | AI 모델이 자동으로 선택하여 호출 |
| 도구 발견 | Swagger 문서를 읽고 개발자가 연동 | AI가 도구 목록을 자동으로 조회 |
| 요청 구성 | 개발자가 URL, 파라미터를 직접 구성 | AI가 자연어를 분석하여 자동 구성 |
| 통합 비용 | 각 API마다 클라이언트 코드 작성 필요 | MCP 클라이언트 하나로 모든 도구 연동 |
| 확장성 | 새 엔드포인트 추가 후 클라이언트 수정 필요 | 새 도구 추가 시 AI가 자동으로 인식 |

### 핵심 차이점

REST API는 **개발자가 API 문서를 읽고 호출 코드를 작성**하는 방식입니다. 새로운 기능이 추가되면 클라이언트 코드를 수정해야 합니다.

MCP는 **AI 모델이 도구 설명을 읽고 스스로 호출을 결정**하는 방식입니다. 새로운 도구를 서버에 추가하면, AI가 자동으로 인식하고 적절한 상황에서 사용합니다. 클라이언트 코드를 수정할 필요가 없습니다.

## 강사 시연 시나리오

### 시연 순서 (약 15분)

**1단계: MCP 서버 구조 설명 (3분)**
- `solution/server.py`를 열어 `@mcp.tool` 데코레이터와 docstring 설명
- "이 docstring이 AI에게 도구 사용법을 알려주는 계약 역할을 합니다"

**2단계: Inspector로 도구 확인 (3분)**
```bash
uv run fastmcp dev inspector solution/server.py
```
- Tools 탭에서 3개 도구를 보여주고, 각각 실행
- "AI 없이도 도구가 정상 동작하는지 먼저 확인합니다"

**3단계: AI 클라이언트 라이브 데모 (5분)**
```bash
uv run python solution/client.py
```
- "김민수 연차 며칠 남았어?" 질문으로 시작
- 콘솔에 출력되는 `[도구 호출]` 로그를 가리키며 브릿지 패턴 설명
- "개발팀 조직도 보여줘", "재택근무 규정 알려줘" 등 추가 질문
- "AI가 질문을 분석하여 적절한 도구를 자동으로 선택하는 점에 주목하십시오"

**4단계: REST API 비교 (4분)**
```bash
uv run python solution/traditional_api.py
```
- Swagger UI를 열어 엔드포인트 구조를 보여줌
- curl로 같은 데이터를 조회: `curl "localhost:8000/api/employees/EMP-001/leave"`
- "REST API는 개발자가 URL과 파라미터를 알아야 합니다. MCP에서는 AI가 알아서 선택합니다"

## 핵심 포인트 정리

1. **MCP는 표준 인터페이스입니다**: AI 모델이 외부 도구에 접근하는 방식을 표준화합니다. 하나의 프로토콜로 다양한 AI 클라이언트와 연동할 수 있습니다.

2. **도구 정의가 곧 API 계약입니다**: `@mcp.tool` 데코레이터와 함수 시그니처(이름, 파라미터, docstring)가 AI 모델에게 도구의 사용법을 알려주는 계약 역할을 합니다.

3. **docstring이 핵심입니다**: AI 모델은 docstring을 읽고 도구를 선택합니다. 명확하고 구체적인 설명이 도구 호출 정확도를 높입니다.

4. **브릿지 패턴으로 연결합니다**: MCP 도구 스키마를 OpenAI function calling 형식으로 변환하면, 자연어 질문에 AI가 자동으로 적절한 도구를 선택합니다.

5. **REST API와 보완 관계입니다**: MCP는 REST API를 대체하는 것이 아니라, AI가 기존 시스템에 접근하는 새로운 인터페이스를 제공합니다.
