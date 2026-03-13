"""
아키텍처 심의위원회(ARB) — 전문가 에이전트 4종
==============================================
각 에이전트는 A2A 프로토콜로 통신하며, 설계 제안서를 자신의 전문 관점에서 리뷰합니다.

에이전트 목록:
  - SecurityReviewAgent  (port 5001): 보안 관점
  - PerformanceReviewAgent (port 5002): 성능 관점
  - CostReviewAgent      (port 5003): 비용 관점
  - OpsReviewAgent       (port 5004): 운영 관점

실행:
  python starter/agents.py
"""

import json
import threading

from python_a2a import (
    A2AServer,
    AgentCard,
    Message,
    MessageRole,
    TextContent,
    run_server,
)


# ============================================================
# 보안 리뷰 에이전트
# ============================================================
class SecurityReviewAgent(A2AServer):
    """보안 관점에서 아키텍처 설계안을 리뷰합니다."""

    def handle_message(self, message):
        """설계안을 받아 보안 관점 분석 결과를 반환합니다."""
        proposal_text = message.content.text if hasattr(message.content, "text") else str(message.content)
        proposal = self._parse_proposal(proposal_text)

        findings = []

        # TODO: 보안 관점에서 설계안을 분석하십시오.
        #
        # 분석해야 할 영역:
        #   1) 데이터 주권 — 퍼블릭 클라우드 사용 시 개인정보보호법 이슈
        #   2) 암호화 — Oracle에서 PostgreSQL 전환 시 암호화 키 관리
        #   3) 접근제어 — EKS 환경의 RBAC, Pod Security, NetworkPolicy
        #   4) 컴플라이언스 — ISMS-P 인증 범위 변경
        #
        # 각 finding은 다음 형식으로 추가하십시오:
        # findings.append({
        #     "category": "분석 영역",
        #     "severity": "높음" | "중간" | "낮음",
        #     "finding": "발견된 문제 상세 설명",
        #     "recommendation": "구체적 권고 사항",
        # })
        #
        # 힌트: proposal["proposed_changes"]["target_cloud"]로 클라우드 종류 확인
        # 힌트: proposal["current_system"]["stack"]으로 현재 기술 스택 확인

        # 종합 의견
        high_count = sum(1 for f in findings if f["severity"] == "높음")

        # TODO: high_count에 따라 verdict를 결정하십시오.
        # 높은 심각도 2건 이상이면 "반려", 그렇지 않으면 "조건부 승인"
        overall = "조건부 승인"

        result = {
            "agent": "보안 리뷰 에이전트",
            "verdict": overall,
            "high_severity_count": high_count,
            "findings": findings,
            "summary": f"보안 관점에서 {len(findings)}건의 검토 의견이 있으며, "
            f"이 중 {high_count}건이 높은 심각도입니다.",
        }

        return Message(
            role=MessageRole.AGENT,
            content=TextContent(text=json.dumps(result, ensure_ascii=False)),
        )

    def _parse_proposal(self, text):
        """텍스트를 JSON 딕셔너리로 파싱합니다."""
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return {}


# ============================================================
# 성능 리뷰 에이전트
# ============================================================
class PerformanceReviewAgent(A2AServer):
    """성능 관점에서 아키텍처 설계안을 리뷰합니다."""

    def handle_message(self, message):
        proposal_text = message.content.text if hasattr(message.content, "text") else str(message.content)
        proposal = self._parse_proposal(proposal_text)

        findings = []

        # TODO: 성능 관점에서 설계안을 분석하십시오.
        #
        # 분석해야 할 영역:
        #   1) 오토스케일링 — EKS의 HPA/VPA를 통한 스케일링 이점 (긍정적)
        #   2) DB 성능 — Oracle에서 PostgreSQL 전환 시 쿼리 성능 저하 가능성
        #   3) 네트워크 레이턴시 — 모놀리식에서 마이크로서비스 전환 시 호출 증가
        #   4) 캐싱 전략 — ElastiCache 도입 필요성
        #
        # 힌트: 스케일링은 긍정적(낮음), DB 전환은 높은 리스크(높음)로 평가하면
        #       에이전트 간 흥미로운 관점 충돌이 발생합니다.

        high_count = sum(1 for f in findings if f["severity"] == "높음")
        overall = "조건부 승인"

        result = {
            "agent": "성능 리뷰 에이전트",
            "verdict": overall,
            "high_severity_count": high_count,
            "findings": findings,
            "summary": f"성능 관점에서 {len(findings)}건의 검토 의견이 있습니다.",
        }

        return Message(
            role=MessageRole.AGENT,
            content=TextContent(text=json.dumps(result, ensure_ascii=False)),
        )

    def _parse_proposal(self, text):
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return {}


# ============================================================
# 비용 리뷰 에이전트
# ============================================================
class CostReviewAgent(A2AServer):
    """비용 관점에서 아키텍처 설계안을 리뷰합니다."""

    def handle_message(self, message):
        proposal_text = message.content.text if hasattr(message.content, "text") else str(message.content)
        proposal = self._parse_proposal(proposal_text)

        findings = []

        # TODO: 비용 관점에서 설계안을 분석하십시오.
        #
        # 분석해야 할 영역:
        #   1) TCO 분석 — 클라우드 3년 운영비 포함 시 온프레미스 대비 비용 비교
        #   2) 라이선스 — Oracle 라이선스 해지 절감 효과
        #   3) 예비비 — 18개월 프로젝트에 예비비 미책정 문제
        #   4) 이중 운영 비용 — Strangler Fig 패턴 적용 시 동시 운영 비용
        #
        # 힌트: proposal["proposed_changes"]["budget"]으로 예산 확인
        # 힌트: 성능 에이전트의 스케일링 긍정 평가와 대비되도록
        #       TCO 관점에서 비용 증가 우려를 제기하면 흥미로운 충돌이 됩니다.

        high_count = sum(1 for f in findings if f["severity"] == "높음")
        overall = "조건부 승인"

        result = {
            "agent": "비용 리뷰 에이전트",
            "verdict": overall,
            "high_severity_count": high_count,
            "findings": findings,
            "summary": f"비용 관점에서 {len(findings)}건의 검토 의견이 있습니다.",
        }

        return Message(
            role=MessageRole.AGENT,
            content=TextContent(text=json.dumps(result, ensure_ascii=False)),
        )

    def _parse_proposal(self, text):
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return {}


# ============================================================
# 운영 리뷰 에이전트
# ============================================================
class OpsReviewAgent(A2AServer):
    """운영 관점에서 아키텍처 설계안을 리뷰합니다."""

    def handle_message(self, message):
        proposal_text = message.content.text if hasattr(message.content, "text") else str(message.content)
        proposal = self._parse_proposal(proposal_text)

        findings = []

        # TODO: 운영 관점에서 설계안을 분석하십시오.
        #
        # 분석해야 할 영역:
        #   1) 팀 역량 — 온프레미스 전문가의 Kubernetes/EKS 역량 부재
        #   2) 모니터링 — 마이크로서비스 전환 시 관측 복잡도 증가
        #   3) 장애 대응 — 15분 복구 목표 달성을 위한 자동화 필요
        #   4) 인력 운영 — 5명에서 2명 감축은 비현실적 (초기 오히려 증가)
        #
        # 힌트: 보안 에이전트가 KMS, PSS 등 고급 보안을 요구하는데,
        #       운영 팀에 그런 역량이 없다고 지적하면 흥미로운 충돌이 됩니다.
        # 힌트: 인력 감축 관련 finding의 severity를 "높음"으로 설정하면
        #       verdict를 "반려"로 판정할 수 있습니다.

        high_count = sum(1 for f in findings if f["severity"] == "높음")

        # TODO: 운영 관점에서 높은 심각도 이슈가 2건 이상이면 "반려"를 판정하십시오.
        overall = "조건부 승인"

        result = {
            "agent": "운영 리뷰 에이전트",
            "verdict": overall,
            "high_severity_count": high_count,
            "findings": findings,
            "summary": f"운영 관점에서 {len(findings)}건의 검토 의견이 있습니다.",
        }

        return Message(
            role=MessageRole.AGENT,
            content=TextContent(text=json.dumps(result, ensure_ascii=False)),
        )

    def _parse_proposal(self, text):
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return {}


# ============================================================
# 에이전트 카드 정의 및 서버 실행
# ============================================================
AGENT_CONFIGS = [
    {
        "cls": SecurityReviewAgent,
        "name": "Security Review Agent",
        "description": "보안 관점에서 아키텍처를 리뷰합니다 (데이터 주권, 암호화, 접근제어, 컴플라이언스)",
        "port": 5001,
    },
    {
        "cls": PerformanceReviewAgent,
        "name": "Performance Review Agent",
        "description": "성능 관점에서 아키텍처를 리뷰합니다 (응답시간, 스케일링, 캐싱, 레이턴시)",
        "port": 5002,
    },
    {
        "cls": CostReviewAgent,
        "name": "Cost Review Agent",
        "description": "비용 관점에서 아키텍처를 리뷰합니다 (TCO, 라이선스, 예비비, 이중운영비)",
        "port": 5003,
    },
    {
        "cls": OpsReviewAgent,
        "name": "Ops Review Agent",
        "description": "운영 관점에서 아키텍처를 리뷰합니다 (팀 역량, 모니터링, 장애 대응, 인력)",
        "port": 5004,
    },
]


def start_agent(config):
    """에이전트 카드를 생성하고 서버를 시작합니다."""
    card = AgentCard(
        name=config["name"],
        description=config["description"],
        url=f"http://localhost:{config['port']}",
        version="1.0.0",
        capabilities={"pushNotifications": False, "stateTransitionHistory": False},
    )
    server = config["cls"](card)
    print(f"  [{config['name']}] http://localhost:{config['port']}")
    run_server(server, host="0.0.0.0", port=config["port"])


if __name__ == "__main__":
    print("=" * 60)
    print("  아키텍처 심의위원회(ARB) — 전문가 에이전트 시작")
    print("=" * 60)
    print()

    threads = []
    for cfg in AGENT_CONFIGS:
        t = threading.Thread(target=start_agent, args=(cfg,), daemon=True)
        t.start()
        threads.append(t)

    print()
    print("  모든 에이전트가 실행 중입니다. Ctrl+C로 종료하십시오.")
    print("=" * 60)

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("\n에이전트를 종료합니다.")
