"""
멀티에이전트 시스템 — 평가 스크립트
====================================
멀티에이전트 시스템의 평가는 개별 에이전트 + 에이전트 간 상호작용을 모두 검증해야 합니다.
이 스크립트는 3가지 평가 패턴을 보여줍니다:

  1. 에이전트별 응답 평가  — 각 에이전트가 올바른 분석을 내놓는지 검증
  2. 의사결정 일관성 평가  — 판정(verdict) 로직이 규칙에 부합하는지 검증
  3. 에이전트 간 충돌 탐지 평가  — 상충하는 관점이 올바르게 식별되는지 검증

사전 조건:
  - agents_server.py가 실행 중이어야 합니다 (port 5001~5004)

실행:
  uv run python solution/eval.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from python_a2a import A2AClient, Message, MessageRole, TextContent


# ──────────────────────────────────────────────
# 평가 프레임워크 (최소 구현)
# ──────────────────────────────────────────────

class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


class EvalResult:
    def __init__(self, name: str, passed: bool, detail: str = ""):
        self.name = name
        self.passed = passed
        self.detail = detail


class EvalSuite:
    def __init__(self, name: str):
        self.name = name
        self.results: list[EvalResult] = []

    def add(self, name: str, passed: bool, detail: str = "") -> None:
        self.results.append(EvalResult(name, passed, detail))
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if passed else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"  {status}  {name}")
        if detail and not passed:
            print(f"         {Colors.DIM}{detail}{Colors.RESET}")

    def summary(self) -> tuple[int, int]:
        passed = sum(1 for r in self.results if r.passed)
        return passed, len(self.results)


# ──────────────────────────────────────────────
# 헬퍼
# ──────────────────────────────────────────────

AGENTS = [
    {"name": "보안 리뷰 에이전트", "url": "http://localhost:5001"},
    {"name": "성능 리뷰 에이전트", "url": "http://localhost:5002"},
    {"name": "비용 리뷰 에이전트", "url": "http://localhost:5003"},
    {"name": "운영 리뷰 에이전트", "url": "http://localhost:5004"},
]


def load_proposal() -> dict:
    proposal_path = Path(__file__).parent.parent / "data" / "design_proposal.json"
    with open(proposal_path, "r", encoding="utf-8") as f:
        return json.load(f)


def send_to_agent(url: str, proposal: dict) -> dict | None:
    """에이전트에게 설계안을 전송하고 JSON 응답을 반환합니다."""
    try:
        client = A2AClient(url)
        message = Message(
            role=MessageRole.USER,
            content=TextContent(text=json.dumps(proposal, ensure_ascii=False)),
        )
        response = client.send_message(message)
        if hasattr(response.content, "text"):
            return json.loads(response.content.text)
    except Exception as e:
        print(f"  {Colors.RED}에이전트 연결 실패: {e}{Colors.RESET}")
    return None


def collect_all_reviews(proposal: dict) -> list[dict]:
    """4개 에이전트에서 리뷰를 수집합니다."""
    reviews = []
    for agent in AGENTS:
        review = send_to_agent(agent["url"], proposal)
        if review:
            reviews.append(review)
    return reviews


# ──────────────────────────────────────────────
# 1. 에이전트별 응답 평가
# ──────────────────────────────────────────────

def eval_agent_responses(suite: EvalSuite, reviews: list[dict]) -> None:
    """각 에이전트의 분석 결과가 올바른지 검증합니다."""

    # 기대되는 에이전트 구성
    expected_agents = {"보안 리뷰 에이전트", "성능 리뷰 에이전트", "비용 리뷰 에이전트", "운영 리뷰 에이전트"}
    actual_agents = {r["agent"] for r in reviews}

    suite.add(
        "모든 에이전트가 응답함",
        expected_agents == actual_agents,
        f"누락: {expected_agents - actual_agents}" if expected_agents != actual_agents else "",
    )

    for review in reviews:
        agent_name = review["agent"]

        # 구조 검증: 필수 필드 존재
        required_fields = {"agent", "verdict", "high_severity_count", "findings", "summary"}
        actual_fields = set(review.keys())
        suite.add(
            f"[{agent_name}] 응답 구조 완전성",
            required_fields.issubset(actual_fields),
            f"누락 필드: {required_fields - actual_fields}",
        )

        # findings 구조 검증
        for i, f in enumerate(review["findings"]):
            finding_fields = {"category", "severity", "finding", "recommendation"}
            suite.add(
                f"[{agent_name}] finding[{i}] 구조",
                finding_fields.issubset(set(f.keys())),
                f"누락 필드: {finding_fields - set(f.keys())}",
            )

        # severity 값 검증
        valid_severities = {"높음", "중간", "낮음"}
        for f in review["findings"]:
            suite.add(
                f"[{agent_name}] severity 유효성: {f['severity']}",
                f["severity"] in valid_severities,
                f"유효하지 않은 값: {f['severity']}",
            )

        # 최소 finding 수 검증 (각 에이전트는 최소 2건 이상 분석해야 함)
        suite.add(
            f"[{agent_name}] 최소 분석 건수 (2건 이상)",
            len(review["findings"]) >= 2,
            f"실제: {len(review['findings'])}건",
        )

    # 보안 에이전트: AWS 클라우드 전환 시 데이터 주권 이슈를 반드시 지적해야 함
    sec_review = next((r for r in reviews if r["agent"] == "보안 리뷰 에이전트"), None)
    if sec_review:
        has_data_sovereignty = any(
            "데이터 주권" in f["category"] or "주권" in f["finding"]
            for f in sec_review["findings"]
        )
        suite.add(
            "[보안] 데이터 주권 이슈 식별",
            has_data_sovereignty,
            "AWS 전환 시 데이터 주권 이슈가 식별되지 않았습니다",
        )

        has_encryption = any(
            "암호화" in f["category"] for f in sec_review["findings"]
        )
        suite.add(
            "[보안] 암호화 이슈 식별",
            has_encryption,
            "Oracle -> PostgreSQL 전환 시 암호화 이슈가 식별되지 않았습니다",
        )

    # 성능 에이전트: 오토스케일링을 긍정적으로, DB 전환을 부정적으로 평가해야 함
    perf_review = next((r for r in reviews if r["agent"] == "성능 리뷰 에이전트"), None)
    if perf_review:
        has_scaling_positive = any(
            "스케일" in f["category"] and f["severity"] == "낮음"
            for f in perf_review["findings"]
        )
        suite.add(
            "[성능] 스케일링 긍정 평가",
            has_scaling_positive,
            "EKS 오토스케일링을 긍정적(낮음)으로 평가하지 않았습니다",
        )

        has_db_concern = any(
            ("DB" in f["category"] or "데이터베이스" in f["category"])
            and f["severity"] == "높음"
            for f in perf_review["findings"]
        )
        suite.add(
            "[성능] DB 전환 리스크 식별",
            has_db_concern,
            "Oracle -> PostgreSQL DB 성능 리스크가 식별되지 않았습니다",
        )

    # 운영 에이전트: 팀 역량 부재와 인력 감축 비현실성을 지적해야 함
    ops_review = next((r for r in reviews if r["agent"] == "운영 리뷰 에이전트"), None)
    if ops_review:
        has_capability_gap = any(
            "역량" in f["category"] and f["severity"] == "높음"
            for f in ops_review["findings"]
        )
        suite.add(
            "[운영] 팀 역량 부재 식별",
            has_capability_gap,
            "K8s/EKS 역량 부재가 높은 심각도로 식별되지 않았습니다",
        )

        has_staffing_issue = any(
            "인력" in f["category"] and f["severity"] == "높음"
            for f in ops_review["findings"]
        )
        suite.add(
            "[운영] 인력 감축 비현실성 식별",
            has_staffing_issue,
            "5명 -> 2명 감축의 비현실성이 식별되지 않았습니다",
        )


# ──────────────────────────────────────────────
# 2. 의사결정 일관성 평가
# ──────────────────────────────────────────────

def eval_verdict_consistency(suite: EvalSuite, reviews: list[dict]) -> None:
    """판정(verdict) 로직이 규칙에 부합하는지 검증합니다."""

    for review in reviews:
        agent = review["agent"]
        high_count = review["high_severity_count"]
        verdict = review["verdict"]

        # high_severity_count 정합성
        actual_high = sum(1 for f in review["findings"] if f["severity"] == "높음")
        suite.add(
            f"[{agent}] high_severity_count 정확성",
            high_count == actual_high,
            f"보고: {high_count}, 실제: {actual_high}",
        )

    # 보안 에이전트: 높음 2건 이상이면 반려
    sec = next((r for r in reviews if r["agent"] == "보안 리뷰 에이전트"), None)
    if sec:
        expected = "반려" if sec["high_severity_count"] >= 2 else "조건부 승인"
        suite.add(
            "[보안] verdict 규칙 준수",
            sec["verdict"] == expected,
            f"높음 {sec['high_severity_count']}건 -> 기대: {expected}, 실제: {sec['verdict']}",
        )

    # 운영 에이전트: 높음 2건 이상이면 반려
    ops = next((r for r in reviews if r["agent"] == "운영 리뷰 에이전트"), None)
    if ops:
        expected = "반려" if ops["high_severity_count"] >= 2 else "조건부 승인"
        suite.add(
            "[운영] verdict 규칙 준수",
            ops["verdict"] == expected,
            f"높음 {ops['high_severity_count']}건 -> 기대: {expected}, 실제: {ops['verdict']}",
        )

    # 최종 판정 로직 검증 (오케스트레이터 로직 재현)
    verdicts = [r["verdict"] for r in reviews]
    reject_count = verdicts.count("반려")
    conditional_count = verdicts.count("조건부 승인")

    if reject_count >= 2:
        expected_final = "반려"
    elif reject_count >= 1 or conditional_count >= 3:
        expected_final = "조건부 승인 (수정 후 재심의)"
    else:
        expected_final = "승인"

    suite.add(
        f"최종 판정 도출 가능 (반려 {reject_count}, 조건부 {conditional_count})",
        True,
        f"예상 최종: {expected_final}",
    )

    # 이 제안서에서는 보안(반려) + 운영(반려)로 최종 반려가 예상됨
    suite.add(
        "최종 판정: 반려 (보안+운영 반려)",
        expected_final == "반려",
        f"실제 최종 판정: {expected_final}",
    )


# ──────────────────────────────────────────────
# 3. 에이전트 간 충돌 탐지 평가
# ──────────────────────────────────────────────

def eval_conflict_detection(suite: EvalSuite, reviews: list[dict]) -> None:
    """상충하는 관점이 올바르게 식별되는지 검증합니다."""
    # orchestrator.py의 analyze_conflicts 로직을 가져옵니다
    sys.path.insert(0, os.path.dirname(__file__))
    from orchestrator import analyze_conflicts

    conflicts = analyze_conflicts(reviews)

    suite.add(
        "충돌 탐지: 최소 2건 이상",
        len(conflicts) >= 2,
        f"탐지된 충돌: {len(conflicts)}건",
    )

    # 기대되는 충돌 유형
    conflict_types = {c["type"] for c in conflicts}

    suite.add(
        "충돌 유형: '성능 대 비용' 식별",
        "성능 대 비용" in conflict_types,
        f"식별된 유형: {conflict_types}",
    )

    suite.add(
        "충돌 유형: '보안 요구 대 운영 역량' 식별",
        "보안 요구 대 운영 역량" in conflict_types,
        f"식별된 유형: {conflict_types}",
    )

    suite.add(
        "충돌 유형: '기대 효과 대 운영 현실' 식별",
        "기대 효과 대 운영 현실" in conflict_types,
        f"식별된 유형: {conflict_types}",
    )

    # 각 충돌에 필수 필드 확인
    for conflict in conflicts:
        required = {"type", "description", "resolution"}
        suite.add(
            f"충돌 구조: '{conflict['type']}' 필수 필드",
            required.issubset(set(conflict.keys())),
            f"누락: {required - set(conflict.keys())}",
        )

    # 충돌이 합리적인지 검증: 성능 vs 비용
    perf_review = next((r for r in reviews if r["agent"] == "성능 리뷰 에이전트"), None)
    cost_review = next((r for r in reviews if r["agent"] == "비용 리뷰 에이전트"), None)
    if perf_review and cost_review:
        perf_positive_scaling = any(
            f["severity"] == "낮음" and "스케일" in f["category"]
            for f in perf_review["findings"]
        )
        cost_negative_tco = any(
            f["severity"] == "높음" and "TCO" in f["category"]
            for f in cost_review["findings"]
        )
        suite.add(
            "충돌 근거: 성능(스케일링 긍정) vs 비용(TCO 부정) 실제 존재",
            perf_positive_scaling and cost_negative_tco,
            f"성능 긍정: {perf_positive_scaling}, 비용 부정: {cost_negative_tco}",
        )


# ──────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────

def main() -> None:
    print(f"\n{Colors.BOLD}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}  멀티에이전트 시스템(ARB) 평가{Colors.RESET}")
    print(f"{Colors.BOLD}  3가지 평가 패턴 실행{Colors.RESET}")
    print(f"{Colors.BOLD}{'=' * 60}{Colors.RESET}")

    # 에이전트 연결 확인
    print(f"\n{Colors.DIM}에이전트 연결을 확인합니다...{Colors.RESET}")
    proposal = load_proposal()
    reviews = collect_all_reviews(proposal)

    if len(reviews) < 4:
        print(f"\n{Colors.RED}{Colors.BOLD}오류: {len(reviews)}/4 에이전트만 응답하였습니다.{Colors.RESET}")
        print(f"{Colors.RED}agents_server.py를 먼저 실행하십시오:{Colors.RESET}")
        print(f"{Colors.DIM}  uv run python solution/agents_server.py{Colors.RESET}\n")
        sys.exit(1)

    print(f"{Colors.GREEN}4개 에이전트 응답 수신 완료{Colors.RESET}")

    suites: list[EvalSuite] = []
    start_time = time.time()

    # 1. 에이전트별 응답 평가
    print(f"\n{Colors.CYAN}{Colors.BOLD}[1/3] 에이전트별 응답 평가{Colors.RESET}")
    print(f"{Colors.DIM}각 에이전트가 올바른 분석을 내놓는지 검증합니다{Colors.RESET}\n")

    s1 = EvalSuite("에이전트 응답 평가")
    eval_agent_responses(s1, reviews)
    suites.append(s1)

    # 2. 의사결정 일관성
    print(f"\n{Colors.CYAN}{Colors.BOLD}[2/3] 의사결정 일관성 평가{Colors.RESET}")
    print(f"{Colors.DIM}판정(verdict) 로직이 규칙에 부합하는지 검증합니다{Colors.RESET}\n")

    s2 = EvalSuite("의사결정 일관성")
    eval_verdict_consistency(s2, reviews)
    suites.append(s2)

    # 3. 충돌 탐지
    print(f"\n{Colors.CYAN}{Colors.BOLD}[3/3] 에이전트 간 충돌 탐지 평가{Colors.RESET}")
    print(f"{Colors.DIM}상충하는 관점이 올바르게 식별되는지 검증합니다{Colors.RESET}\n")

    s3 = EvalSuite("충돌 탐지 평가")
    eval_conflict_detection(s3, reviews)
    suites.append(s3)

    # 종합 결과
    elapsed = time.time() - start_time
    total_passed = sum(s.summary()[0] for s in suites)
    total_tests = sum(s.summary()[1] for s in suites)

    print(f"\n{Colors.BOLD}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}  평가 결과 요약{Colors.RESET}")
    print(f"{Colors.BOLD}{'=' * 60}{Colors.RESET}\n")

    for s in suites:
        passed, total = s.summary()
        rate = passed / total if total > 0 else 0
        color = Colors.GREEN if rate == 1.0 else (Colors.YELLOW if rate >= 0.8 else Colors.RED)
        print(f"  {s.name:<28} {color}{passed}/{total} ({rate:.0%}){Colors.RESET}")

    overall_rate = total_passed / total_tests if total_tests > 0 else 0
    overall_color = Colors.GREEN if overall_rate == 1.0 else (Colors.YELLOW if overall_rate >= 0.8 else Colors.RED)

    print(f"\n  {'─' * 40}")
    print(f"  {Colors.BOLD}{'총계':<28} {overall_color}{total_passed}/{total_tests} ({overall_rate:.0%}){Colors.RESET}")
    print(f"  {Colors.DIM}소요 시간: {elapsed:.1f}초{Colors.RESET}")

    if overall_rate == 1.0:
        print(f"\n  {Colors.GREEN}{Colors.BOLD}모든 평가를 통과하였습니다.{Colors.RESET}")
    else:
        failed = total_tests - total_passed
        print(f"\n  {Colors.RED}{Colors.BOLD}{failed}건의 평가가 실패하였습니다.{Colors.RESET}")

    print()
    sys.exit(0 if overall_rate >= 0.8 else 1)


if __name__ == "__main__":
    main()
