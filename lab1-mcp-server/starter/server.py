"""
Lab 1: FastMCP HR 도구 서버 (학생용 스타터 코드)

사내 AI 어시스턴트가 HR 시스템에 접근할 수 있도록
MCP 프로토콜 기반 도구 서버를 구현합니다.

아래 TODO 표시된 부분을 채워서 완성하십시오.
"""

import json
from pathlib import Path

from fastmcp import FastMCP

# MCP 서버 인스턴스 생성
mcp = FastMCP("HR Assistant Tools")

# 데이터 파일 경로 설정 (server.py 기준 상대 경로)
DATA_DIR = Path(__file__).parent.parent / "data"


def load_json(filename: str) -> list | dict:
    """JSON 데이터 파일을 읽어서 반환합니다."""
    file_path = DATA_DIR / filename
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


@mcp.tool
def search_hr_policy(query: str) -> str:
    """사내 HR 규정을 키워드로 검색합니다.

    Args:
        query: 검색할 키워드 (예: "연차", "재택근무", "보안")

    Returns:
        검색 결과 문자열. 매칭되는 규정의 제목과 내용을 반환합니다.
    """
    # TODO: 여기에 구현하세요
    # 힌트 1: load_json("hr_policies.json")으로 규정 데이터를 불러옵니다
    # 힌트 2: query.split()으로 키워드를 분리하고, 각 규정의 title, category, content에서 검색합니다
    # 힌트 3: 매칭되는 규정이 없으면 안내 메시지를 반환합니다
    raise NotImplementedError("TODO: 이 함수를 구현하십시오")


@mcp.tool
def get_leave_balance(employee_id: str) -> dict:
    """직원의 연차 잔여일을 조회합니다.

    Args:
        employee_id: 직원 사번 (예: "EMP-001")

    Returns:
        직원명, 총 연차일수, 사용일수, 잔여일수를 포함하는 딕셔너리
    """
    # TODO: 여기에 구현하세요
    # 힌트 1: load_json("employees.json")으로 직원 데이터를 불러옵니다
    # 힌트 2: employee_id가 일치하는 직원을 찾아 연차 정보를 반환합니다
    # 힌트 3: 직원을 찾지 못하면 error 키가 포함된 딕셔너리를 반환합니다
    raise NotImplementedError("TODO: 이 함수를 구현하십시오")


@mcp.tool
def lookup_org_chart(department: str) -> dict:
    """부서별 조직도를 조회합니다.

    Args:
        department: 부서명 (예: "개발팀", "인사팀", "기획팀")

    Returns:
        부서장, 팀원 목록, 하위 조직을 포함하는 딕셔너리
    """
    # TODO: 여기에 구현하세요
    # 힌트 1: load_json("org_chart.json")으로 조직도 데이터를 불러옵니다
    # 힌트 2: department 키로 해당 부서 정보를 조회합니다
    # 힌트 3: 부서를 찾지 못하면 사용 가능한 부서 목록을 안내합니다
    raise NotImplementedError("TODO: 이 함수를 구현하십시오")


if __name__ == "__main__":
    mcp.run()
