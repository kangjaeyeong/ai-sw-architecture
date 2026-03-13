# Lab 1: FastMCP HR 도구 서버 구축

## 실습 목표

사내 AI 어시스턴트가 HR 시스템에 접근할 수 있도록 MCP(Model Context Protocol) 서버를 구축합니다. 이 실습을 통해 다음을 학습합니다.

- MCP 프로토콜의 도구(Tool) 개념을 이해합니다
- FastMCP 라이브러리로 도구 서버를 구현합니다
- AI 에이전트가 외부 시스템과 연동하는 패턴을 직접 체험합니다

**소요 시간**: 약 15분

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

### Step 6: 서버 실행 및 테스트

작성을 완료한 후 아래 단계를 따라 테스트합니다.

## 실행 및 테스트 방법

### 서버 실행

스타터 코드를 완성했다면, 아래 명령어로 MCP 서버를 실행합니다.

```bash
# starter 코드를 완성한 경우
uv run python starter/server.py

# 또는 solution 코드로 바로 확인하는 경우
uv run python solution/server.py
```

서버가 정상 실행되면 stdio 모드로 MCP 요청을 대기합니다.

### MCP Inspector로 테스트

FastMCP에 내장된 Inspector를 사용하여 브라우저에서 테스트할 수 있습니다.

```bash
uv run fastmcp dev solution/server.py
```

Inspector가 실행되면 브라우저에서 다음을 시도하십시오.

1. Tools 탭에서 등록된 3개 도구를 확인합니다
2. `search_hr_policy`에 "연차"를 입력하여 검색 결과를 확인합니다
3. `get_leave_balance`에 "EMP-001"을 입력하여 연차 잔여일을 확인합니다
4. `lookup_org_chart`에 "개발팀"을 입력하여 조직도를 확인합니다

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

## 핵심 포인트 정리

1. **MCP는 표준 인터페이스입니다**: AI 모델이 외부 도구에 접근하는 방식을 표준화합니다. 하나의 프로토콜로 다양한 AI 클라이언트와 연동할 수 있습니다.

2. **도구 정의가 곧 API 계약입니다**: `@mcp.tool` 데코레이터와 함수 시그니처(이름, 파라미터, docstring)가 AI 모델에게 도구의 사용법을 알려주는 계약 역할을 합니다.

3. **docstring이 핵심입니다**: AI 모델은 docstring을 읽고 도구를 선택합니다. 명확하고 구체적인 설명이 도구 호출 정확도를 높입니다.

4. **반환 타입을 명시하십시오**: `str`, `dict` 등 반환 타입을 명확히 지정하면 AI 모델이 응답을 올바르게 해석할 수 있습니다.

5. **에러 처리를 포함하십시오**: 데이터를 찾지 못한 경우에도 구조화된 응답을 반환하여 AI 모델이 사용자에게 적절한 안내를 할 수 있도록 합니다.
