"""
아키텍처 심의위원회(ARB) — 오케스트레이터
==========================================
설계 제안서를 4명의 전문가 에이전트에게 전달하고,
리뷰 결과를 수집하여 종합 심의 보고서를 생성합니다.

사전 조건:
  - agents.py가 실행 중이어야 합니다 (port 5001~5004)

실행:
  python solution/orchestrator.py              # 규칙 기반 분석
  python solution/orchestrator.py --use-llm    # LLM 기반 분석 (API 키 필요)
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
            client = A2AClient(agent_info["url"])
            message = Message(
                role=MessageRole.USER,
                content=TextContent(text=proposal_text),
            )

            start_time = time.time()
            response = client.send_message(message)
            elapsed = time.time() - start_time

            # 응답에서 에이전트 메시지 추출
            response_text = None
            if hasattr(response, "content") and response.content:
                response_text = response.content.text

            if response_text:
                review = json.loads(response_text)
                reviews.append(review)
                print(f"  {color}  응답 수신 완료 ({elapsed:.1f}초) "
                      f"- 판정: {review['verdict']}{Colors.END}")
            else:
                print(f"  {Colors.RED}  응답 파싱 실패{Colors.END}")

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

    # 에이전트별 verdict 수집
    verdicts = {r["agent"]: r["verdict"] for r in reviews}

    # 충돌 1: 성능 vs 비용 (스케일링 긍정 vs TCO 우려)
    perf_review = next((r for r in reviews if r["agent"] == "성능 리뷰 에이전트"), None)
    cost_review = next((r for r in reviews if r["agent"] == "비용 리뷰 에이전트"), None)
    if perf_review and cost_review:
        perf_positive = any(
            f["severity"] == "낮음" and "스케일링" in f["category"]
            for f in perf_review["findings"]
        )
        cost_concern = any(
            f["severity"] == "높음" and "TCO" in f["category"]
            for f in cost_review["findings"]
        )
        if perf_positive and cost_concern:
            conflicts.append(
                {
                    "type": "성능 대 비용",
                    "description": "성능 에이전트는 오토스케일링을 긍정적으로 평가하나, "
                    "비용 에이전트는 3년 TCO 증가를 우려합니다.",
                    "resolution": "성능 SLA를 정의한 후 비용 최적화(RI, Spot) 전략을 "
                    "함께 수립하여 균형점을 찾아야 합니다.",
                }
            )

    # 충돌 2: 보안 vs 운영 (보안 강화 vs 역량 부족)
    sec_review = next((r for r in reviews if r["agent"] == "보안 리뷰 에이전트"), None)
    ops_review = next((r for r in reviews if r["agent"] == "운영 리뷰 에이전트"), None)
    if sec_review and ops_review:
        sec_demands = [f for f in sec_review["findings"] if f["severity"] == "높음"]
        ops_capacity = any(
            "역량" in f["category"] and f["severity"] == "높음"
            for f in ops_review["findings"]
        )
        if sec_demands and ops_capacity:
            conflicts.append(
                {
                    "type": "보안 요구 대 운영 역량",
                    "description": "보안 에이전트는 KMS, PSS, NetworkPolicy 등 고급 보안 체계를 "
                    "요구하나, 운영 에이전트는 팀의 클라우드 역량 부재를 지적합니다.",
                    "resolution": "보안 요구사항을 단계별로 나누어 Phase 1에서는 기본 보안만 적용하고, "
                    "팀 역량 성장에 맞춰 점진적으로 강화해야 합니다.",
                }
            )

    # 충돌 3: 제안서 목표 vs 운영 현실
    if ops_review:
        ops_rejects_staffing = any(
            "인력" in f["category"] and f["severity"] == "높음"
            for f in ops_review["findings"]
        )
        if ops_rejects_staffing:
            conflicts.append(
                {
                    "type": "기대 효과 대 운영 현실",
                    "description": "제안서는 운영 인력 60% 감축을 기대하나, "
                    "운영 에이전트는 전환 초기 오히려 인력 증가가 필요하다고 판단합니다.",
                    "resolution": "인력 감축 목표를 전환 완료 후 12개월 시점으로 재설정하고, "
                    "기존 인력 재교육(reskilling) 계획을 수립해야 합니다.",
                }
            )

    return conflicts


# ============================================================
# 최종 심의 보고서 생성
# ============================================================
def generate_final_report(proposal, reviews, conflicts):
    """종합 심의 보고서를 생성하고 출력합니다."""

    # 종합 판정 결정
    verdicts = [r["verdict"] for r in reviews]
    reject_count = verdicts.count("반려")
    conditional_count = verdicts.count("조건부 승인")

    if reject_count >= 2:
        final_verdict = "반려"
        verdict_color = Colors.RED
    elif reject_count >= 1 or conditional_count >= 3:
        final_verdict = "조건부 승인 (수정 후 재심의)"
        verdict_color = Colors.YELLOW
    else:
        final_verdict = "승인"
        verdict_color = Colors.GREEN

    # 전체 findings 심각도 집계
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

    # 주요 발견 사항 (높음만)
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
    print()
    print(f"{Colors.BOLD}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}  최종 판정: {verdict_color}{final_verdict}{Colors.END}")
    print(f"{Colors.BOLD}{'=' * 60}{Colors.END}")

    # 선행 조건 (조건부 승인인 경우)
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
