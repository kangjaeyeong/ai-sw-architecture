"""
아키텍처 심의위원회(ARB) — 오케스트레이터
==========================================
설계 제안서를 4명의 전문가 에이전트에게 전달하고,
리뷰 결과를 수집하여 종합 심의 보고서를 생성합니다.

사전 조건:
  - agents.py가 실행 중이어야 합니다 (port 5001~5004)

실행:
  python starter/orchestrator.py
"""

import argparse
import json
import sys
import time
from pathlib import Path

from python_a2a import A2AClient, Message, MessageRole, TextContent


# ============================================================
# 터미널 출력 헬퍼
# ============================================================
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


def print_header(text):
    print()
    print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}  {text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 60}{Colors.END}")


def print_section(text, color=Colors.CYAN):
    print()
    print(f"{color}{Colors.BOLD}--- {text} ---{Colors.END}")


def print_finding(finding, index):
    severity = finding["severity"]
    if severity == "높음":
        sev_color = Colors.RED
    elif severity == "중간":
        sev_color = Colors.YELLOW
    else:
        sev_color = Colors.GREEN

    print(f"  {index}. [{sev_color}{Colors.BOLD}{severity}{Colors.END}] "
          f"{Colors.BOLD}{finding['category']}{Colors.END}")
    print(f"     발견: {finding['finding']}")
    print(f"     {Colors.CYAN}권고: {finding['recommendation']}{Colors.END}")
    print()


# ============================================================
# 에이전트 설정
# ============================================================
AGENTS = [
    {"name": "보안 리뷰 에이전트", "url": "http://localhost:5001", "icon": "[보안]"},
    {"name": "성능 리뷰 에이전트", "url": "http://localhost:5002", "icon": "[성능]"},
    {"name": "비용 리뷰 에이전트", "url": "http://localhost:5003", "icon": "[비용]"},
    {"name": "운영 리뷰 에이전트", "url": "http://localhost:5004", "icon": "[운영]"},
]

AGENT_COLORS = [Colors.RED, Colors.BLUE, Colors.YELLOW, Colors.GREEN]


# ============================================================
# 설계 제안서 로드
# ============================================================
def load_proposal(filename: str = "design_proposal.json"):
    """설계 제안서를 로드합니다."""
    proposal_path = Path(__file__).parent.parent / "data" / filename
    if not proposal_path.exists():
        print(f"{Colors.RED}오류: 설계 제안서를 찾을 수 없습니다: {proposal_path}{Colors.END}")
        sys.exit(1)

    with open(proposal_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# 에이전트 리뷰 수집
# ============================================================
def collect_reviews(proposal):
    """각 전문가 에이전트에게 설계안을 전송하고 리뷰를 수집합니다."""
    proposal_text = json.dumps(proposal, ensure_ascii=False)
    reviews = []

    for i, agent_info in enumerate(AGENTS):
        color = AGENT_COLORS[i]
        print(f"\n  {color}{Colors.BOLD}{agent_info['icon']}{Colors.END} "
              f"{agent_info['name']}에게 리뷰를 요청합니다...")

        try:
            # TODO: A2AClient를 사용하여 에이전트에게 설계안을 전송하십시오.
            #
            # 1. A2AClient 생성: client = A2AClient(agent_info["url"])
            # 2. Message 생성: message = Message(role=MessageRole.USER, content=TextContent(text=proposal_text))
            # 3. 전송: response = client.send_message(message)
            # 4. 응답에서 텍스트 추출: response.content.text
            # 5. JSON 파싱 후 reviews 리스트에 추가하십시오.
            pass

        except Exception as e:
            print(f"  {Colors.RED}  연결 실패: {e}{Colors.END}")
            print(f"  {Colors.RED}  agents.py가 실행 중인지 확인하십시오.{Colors.END}")

    return reviews


# ============================================================
# 충돌 분석
# ============================================================
def analyze_conflicts(reviews):
    """에이전트 간 상충하는 의견을 식별합니다."""
    conflicts = []

    # TODO: 에이전트 간 관점 충돌을 식별하십시오.
    #
    # 식별해야 할 충돌 유형:
    #
    # 1) 성능 대 비용:
    #    - 성능 에이전트가 스케일링을 긍정(severity "낮음")으로 평가했는데
    #    - 비용 에이전트가 TCO를 부정(severity "높음")으로 평가한 경우
    #    힌트: 각 review의 findings를 순회하며 category와 severity를 비교
    #
    # 2) 보안 요구 대 운영 역량:
    #    - 보안 에이전트가 높은 심각도로 고급 보안 체계를 요구하는데
    #    - 운영 에이전트가 팀 역량 부재를 높은 심각도로 지적한 경우
    #
    # 3) 기대 효과 대 운영 현실:
    #    - 제안서가 인력 감축을 기대하는데
    #    - 운영 에이전트가 인력 관련 높은 심각도 이슈를 제기한 경우
    #
    # 각 충돌은 다음 형식으로 추가하십시오:
    # conflicts.append({
    #     "type": "충돌 유형 이름",
    #     "description": "충돌 상세 설명",
    #     "resolution": "해결 방안 제시",
    # })

    return conflicts


# ============================================================
# 최종 심의 보고서 생성
# ============================================================
def generate_final_report(proposal, reviews, conflicts):
    """종합 심의 보고서를 생성하고 출력합니다."""

    # TODO: 종합 판정을 결정하십시오.
    #
    # 규칙:
    #   - "반려" 판정이 2건 이상: 최종 "반려"
    #   - "반려" 1건 또는 "조건부 승인" 3건 이상: "조건부 승인 (수정 후 재심의)"
    #   - 그 외: "승인"
    verdicts = [r["verdict"] for r in reviews]
    final_verdict = "조건부 승인 (수정 후 재심의)"  # TODO: 위 규칙에 따라 결정

    # 전체 findings 집계
    all_findings = []
    for r in reviews:
        all_findings.extend(r["findings"])

    high = sum(1 for f in all_findings if f["severity"] == "높음")
    medium = sum(1 for f in all_findings if f["severity"] == "중간")
    low = sum(1 for f in all_findings if f["severity"] == "낮음")

    # ---- 출력 ----
    print_header("아키텍처 심의위원회(ARB) 종합 보고서")

    # 제안 개요
    print_section("1. 심의 대상", Colors.BLUE)
    print(f"  제목: {proposal['title']}")
    print(f"  제안 부서: {proposal['proposer']}")
    print(f"  제안 일자: {proposal['date']}")
    print(f"  핵심 내용: {proposal['summary']}")

    # 에이전트별 판정 요약
    print_section("2. 전문가별 판정", Colors.BLUE)
    for i, review in enumerate(reviews):
        color = AGENT_COLORS[i]
        v = review["verdict"]
        if v == "반려":
            v_color = Colors.RED
        elif v == "조건부 승인":
            v_color = Colors.YELLOW
        else:
            v_color = Colors.GREEN

        print(f"  {color}{Colors.BOLD}{review['agent']}{Colors.END}: "
              f"{v_color}{Colors.BOLD}{v}{Colors.END}")
        print(f"    {review['summary']}")
        print()

    # 높은 심각도 발견 사항
    print_section("3. 높은 심각도 발견 사항", Colors.RED)
    idx = 1
    for review in reviews:
        for finding in review["findings"]:
            if finding["severity"] == "높음":
                print(f"  {Colors.BOLD}{review['agent']}{Colors.END}")
                print_finding(finding, idx)
                idx += 1

    # 관점 충돌 분석
    if conflicts:
        print_section("4. 관점 충돌 분석", Colors.YELLOW)
        for i, conflict in enumerate(conflicts, 1):
            print(f"  {Colors.BOLD}{i}. [{conflict['type']}]{Colors.END}")
            print(f"     충돌: {conflict['description']}")
            print(f"     {Colors.CYAN}해결 방안: {conflict['resolution']}{Colors.END}")
            print()

    # 통계
    print_section("5. 검토 통계", Colors.BLUE)
    print(f"  총 발견 사항: {len(all_findings)}건")
    print(f"    {Colors.RED}높음: {high}건{Colors.END}  "
          f"{Colors.YELLOW}중간: {medium}건{Colors.END}  "
          f"{Colors.GREEN}낮음: {low}건{Colors.END}")
    print(f"  관점 충돌: {len(conflicts)}건")

    # 최종 판정
    if "반려" in final_verdict:
        verdict_color = Colors.RED
    elif "조건부" in final_verdict:
        verdict_color = Colors.YELLOW
    else:
        verdict_color = Colors.GREEN

    print()
    print(f"{Colors.BOLD}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}  최종 판정: {verdict_color}{final_verdict}{Colors.END}")
    print(f"{Colors.BOLD}{'=' * 60}{Colors.END}")

    # 선행 조건
    if "조건부" in final_verdict or final_verdict == "반려":
        print_section("6. 재심의 선행 조건", Colors.CYAN)
        conditions = []
        for review in reviews:
            for finding in review["findings"]:
                if finding["severity"] == "높음":
                    conditions.append(
                        f"[{review['agent']}] {finding['recommendation']}"
                    )

        for i, cond in enumerate(conditions, 1):
            print(f"  {i}. {cond}")

        print()
        print(f"  {Colors.BOLD}위 조건을 충족한 후 재심의를 요청하십시오.{Colors.END}")

    print()


# ============================================================
# 메인
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="아키텍처 심의위원회(ARB) 오케스트레이터"
    )
    parser.add_argument(
        "--proposal",
        default="design_proposal.json",
        help="제안서 파일명 (기본: design_proposal.json, v2: design_proposal_v2.json)",
    )
    args = parser.parse_args()

    # 1. 설계 제안서 로드
    print_header("아키텍처 심의위원회(ARB) 시작")
    print(f"\n  설계 제안서를 로드합니다... ({args.proposal})")
    proposal = load_proposal(args.proposal)
    print(f"  제안: {Colors.BOLD}{proposal['title']}{Colors.END}")
    print(f"  예산: {proposal['proposed_changes']['budget']}")
    print(f"  기간: {proposal['proposed_changes']['timeline']}")

    # 2. 전문가 에이전트에게 리뷰 요청
    print_section("전문가 리뷰 수집", Colors.CYAN)
    reviews = collect_reviews(proposal)

    if not reviews:
        print(f"\n{Colors.RED}오류: 수집된 리뷰가 없습니다. "
              f"agents.py가 실행 중인지 확인하십시오.{Colors.END}")
        sys.exit(1)

    print(f"\n  {Colors.GREEN}{len(reviews)}명의 전문가로부터 리뷰를 수집했습니다.{Colors.END}")

    # 3. 관점 충돌 분석
    print_section("관점 충돌 분석 중...", Colors.YELLOW)
    conflicts = analyze_conflicts(reviews)
    print(f"  {len(conflicts)}건의 관점 충돌을 식별했습니다.")

    # 4. 종합 보고서 생성
    generate_final_report(proposal, reviews, conflicts)


if __name__ == "__main__":
    main()
