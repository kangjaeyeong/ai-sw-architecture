"""
Lab 1: FastMCP HR 도구 서버 (완성 코드)

사내 AI 어시스턴트가 HR 시스템에 접근할 수 있도록
MCP 프로토콜 기반 도구 서버를 구현합니다.
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
    policies = load_json("hr_policies.json")

    # 키워드 매칭으로 관련 규정 검색
    results = []
    for policy in policies:
        # 제목, 카테고리, 내용에서 키워드를 검색합니다
        searchable = f"{policy['title']} {policy['category']} {policy['content']}".lower()
        keywords = query.lower().split()
        if any(kw in searchable for kw in keywords):
            results.append(
                f"[{policy['id']}] {policy['title']}\n{policy['content']}"
            )

    if not results:
        return f"'{query}' 관련 규정을 찾을 수 없습니다."

    return "\n\n---\n\n".join(results)


@mcp.tool
def get_leave_balance(employee_id: str) -> dict:
    """직원의 연차 잔여일을 조회합니다.

    Args:
        employee_id: 직원 사번 (예: "EMP-001")

    Returns:
        직원명, 총 연차일수, 사용일수, 잔여일수를 포함하는 딕셔너리
    """
    employees = load_json("employees.json")

    # 사번으로 직원 정보를 검색합니다
    for emp in employees:
        if emp["employee_id"] == employee_id:
            return {
                "employee_id": emp["employee_id"],
                "name": emp["name"],
                "department": emp["department"],
                "total_leave": emp["total_leave"],
                "used_leave": emp["used_leave"],
                "remaining_leave": emp["remaining_leave"],
            }

    return {"error": f"사번 '{employee_id}'에 해당하는 직원을 찾을 수 없습니다."}


@mcp.tool
def lookup_org_chart(department: str) -> dict:
    """부서별 조직도를 조회합니다.

    Args:
        department: 부서명 (예: "개발팀", "인사팀", "기획팀")

    Returns:
        부서장, 팀원 목록, 하위 조직을 포함하는 딕셔너리
    """
    org_chart = load_json("org_chart.json")

    # 부서명으로 조직도를 검색합니다
    if department in org_chart:
        dept_info = org_chart[department]
        return {
            "department": department,
            "department_id": dept_info["department_id"],
            "head": dept_info["head"],
            "head_position": dept_info["head_position"],
            "members": dept_info["members"],
            "sub_teams": dept_info["sub_teams"],
            "total_members": len(dept_info["members"]) + 1,  # 팀장 포함
        }

    # 부서를 찾지 못한 경우, 사용 가능한 부서 목록을 안내합니다
    available = list(org_chart.keys())
    return {
        "error": f"'{department}' 부서를 찾을 수 없습니다.",
        "available_departments": available,
    }


if __name__ == "__main__":
    mcp.run()
