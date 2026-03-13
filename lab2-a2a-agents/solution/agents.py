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
  python solution/agents.py
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

        # 1) 데이터 주권 분석
        if proposal.get("proposed_changes", {}).get("target_cloud") == "AWS":
            findings.append(
                {
                    "category": "데이터 주권",
                    "severity": "높음",
                    "finding": "퍼블릭 클라우드 전환 시 개인정보보호법 및 데이터 3법에 따른 "
                    "국내 데이터 저장 의무 검토가 필요합니다. "
                    "AWS 서울 리전 사용을 필수 요건으로 지정해야 합니다.",
                    "recommendation": "데이터 분류 체계를 수립하고, 민감 데이터는 국내 리전에만 "
                    "저장하는 정책을 설계 단계에서 확정하십시오.",
                }
            )

        # 2) 암호화 분석
        if "Oracle" in proposal.get("current_system", {}).get("stack", ""):
            findings.append(
                {
                    "category": "암호화",
                    "severity": "높음",
                    "finding": "Oracle DB에서 Aurora PostgreSQL 전환 시 기존 TDE(Transparent Data "
                    "Encryption) 설정이 유실될 수 있습니다. "
                    "전환 과정에서 암호화 키 관리 체계를 재수립해야 합니다.",
                    "recommendation": "AWS KMS 기반 암호화 키 관리를 도입하고, "
                    "전송 중 암호화(TLS 1.3)와 저장 시 암호화(AES-256)를 모두 적용하십시오.",
                }
            )

        # 3) 접근제어 분석
        if "EKS" in proposal.get("proposed_changes", {}).get("architecture", ""):
            findings.append(
                {
                    "category": "접근제어",
                    "severity": "중간",
                    "finding": "EKS 클러스터의 RBAC 설정이 제안서에 명시되어 있지 않습니다. "
                    "컨테이너 환경에서는 네트워크 정책과 Pod 보안 표준이 필수입니다.",
                    "recommendation": "Pod Security Standards(PSS) Restricted 프로파일을 적용하고, "
                    "네임스페이스별 NetworkPolicy를 설계하십시오.",
                }
            )

        # 4) 컴플라이언스 분석
        findings.append(
            {
                "category": "컴플라이언스",
                "severity": "중간",
                "finding": "클라우드 전환 시 ISMS-P 인증 범위 변경 신고가 필요합니다. "
                "기존 온프레미스 기준의 보안 통제 항목을 클라우드 환경에 맞게 재매핑해야 합니다.",
                "recommendation": "전환 착수 전 ISMS-P 인증 기관에 범위 변경을 사전 협의하고, "
                "CSA STAR 인증 기반으로 클라우드 보안 통제를 재설계하십시오.",
            }
        )

        # 종합 의견
        high_count = sum(1 for f in findings if f["severity"] == "높음")
        overall = "반려" if high_count >= 2 else "조건부 승인"

        result = {
            "agent": "보안 리뷰 에이전트",
            "verdict": overall,
            "high_severity_count": high_count,
            "findings": findings,
            "summary": f"보안 관점에서 {len(findings)}건의 검토 의견이 있으며, "
            f"이 중 {high_count}건이 높은 심각도입니다. "
            f"데이터 주권과 암호화 문제를 해결하기 전까지 전환을 보류할 것을 권고합니다.",
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

        # 1) 스케일링 분석
        current = proposal.get("current_system", {})
        proposed = proposal.get("proposed_changes", {})

        if "EKS" in proposed.get("architecture", ""):
            findings.append(
                {
                    "category": "오토스케일링",
                    "severity": "낮음",
                    "finding": "EKS 기반 컨테이너 아키텍처는 HPA/VPA를 통한 자동 스케일링이 "
                    "가능하여 현재 스케일링 한계 문제를 근본적으로 해결할 수 있습니다.",
                    "recommendation": "HPA 메트릭 기준(CPU 70%, Memory 80%)과 "
                    "최대 Pod 수를 사전에 정의하십시오.",
                }
            )

        # 2) DB 성능 분석
        if "Aurora" in proposed.get("database", ""):
            findings.append(
                {
                    "category": "데이터베이스 성능",
                    "severity": "높음",
                    "finding": "Oracle에서 PostgreSQL로의 전환 시 PL/SQL 프로시저, "
                    "힌트 기반 쿼리, 시퀀스 동작 차이로 인해 "
                    "20% 이상의 쿼리 성능 저하가 발생할 수 있습니다. "
                    "특히 500명 동시 접속 기준 응답 시간 SLA 충족이 불확실합니다.",
                    "recommendation": "전환 전 상위 50개 슬로우 쿼리를 식별하여 "
                    "PostgreSQL 호환성을 검증하고, 필요 시 쿼리 재작성 일정을 반영하십시오.",
                }
            )

        # 3) 네트워크 레이턴시
        findings.append(
            {
                "category": "네트워크 레이턴시",
                "severity": "중간",
                "finding": "마이크로서비스 전환 시 서비스 간 네트워크 호출이 증가하여 "
                "단일 트랜잭션 레이턴시가 현재 대비 30 ~ 50% 증가할 수 있습니다. "
                "현재 모놀리식 구조에서는 인메모리 호출이던 것이 네트워크 호출로 전환됩니다.",
                "recommendation": "서비스 메시(Istio 등) 도입과 함께 gRPC 프로토콜을 적용하고, "
                "핵심 경로의 레이턴시 버짓을 사전에 정의하십시오.",
            }
        )

        # 4) 캐싱 전략
        findings.append(
            {
                "category": "캐싱 전략",
                "severity": "중간",
                "finding": "제안서에 캐싱 전략이 명시되어 있지 않습니다. "
                "클라우드 전환 시 ElastiCache(Redis) 도입으로 "
                "DB 부하를 60% 이상 줄일 수 있으나, 캐시 무효화 전략이 필요합니다.",
                "recommendation": "읽기 빈도가 높은 조회 API를 식별하고, "
                "캐시 TTL과 무효화 정책을 설계에 포함하십시오.",
            }
        )

        high_count = sum(1 for f in findings if f["severity"] == "높음")
        overall = "조건부 승인"

        result = {
            "agent": "성능 리뷰 에이전트",
            "verdict": overall,
            "high_severity_count": high_count,
            "findings": findings,
            "summary": f"성능 관점에서 클라우드 전환은 스케일링 측면에서 긍정적이나, "
            f"DB 전환 시 쿼리 성능 저하({high_count}건 높은 심각도)와 "
            f"마이크로서비스 레이턴시 증가에 대한 대책이 필요합니다.",
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
        proposed = proposal.get("proposed_changes", {})

        # 1) TCO 분석
        budget = proposed.get("budget", "")
        findings.append(
            {
                "category": "총 소유 비용(TCO)",
                "severity": "높음",
                "finding": f"제안된 예산 {budget}은 마이그레이션 비용만 포함한 것으로 보입니다. "
                "클라우드 전환 후 3년간 운영비(월 약 2,500만원 예상)를 합산하면 "
                "총 TCO는 약 21억원으로, 온프레미스 유지 비용(약 15억원) 대비 "
                "40% 높을 수 있습니다. 3년 차부터 손익 분기에 도달합니다.",
                "recommendation": "온프레미스 유지 시나리오와 클라우드 전환 시나리오의 "
                "5년 TCO 비교표를 작성하여 경영진에게 제출하십시오.",
            }
        )

        # 2) 라이선스 비용
        if "Oracle" in proposal.get("current_system", {}).get("stack", ""):
            findings.append(
                {
                    "category": "라이선스",
                    "severity": "낮음",
                    "finding": "Oracle DB 라이선스 해지 시 연간 약 3억원의 비용 절감이 가능합니다. "
                    "다만 Oracle 라이선스 계약의 잔여 기간과 위약금을 확인해야 합니다.",
                    "recommendation": "Oracle 라이선스 계약 잔여 기간을 확인하고, "
                    "조기 해지 시 위약금 발생 여부를 법무팀과 검토하십시오.",
                }
            )

        # 3) 예비비 부재
        findings.append(
            {
                "category": "예비비",
                "severity": "중간",
                "finding": "18개월 프로젝트에서 예비비(contingency)가 책정되어 있지 않습니다. "
                "클라우드 마이그레이션 프로젝트의 평균 예산 초과율은 23%이며, "
                "최소 15%의 예비비를 확보해야 합니다.",
                "recommendation": "전체 예산의 15%(약 1.8억원)를 예비비로 별도 확보하고, "
                "월별 비용 추적 체계를 수립하십시오.",
            }
        )

        # 4) 이중 운영 비용
        if proposed.get("migration_strategy") == "Strangler Fig 패턴 (단계적 전환)":
            findings.append(
                {
                    "category": "이중 운영 비용",
                    "severity": "중간",
                    "finding": "Strangler Fig 패턴을 적용할 경우 전환 기간(18개월) 동안 "
                    "온프레미스와 클라우드를 동시에 운영해야 합니다. "
                    "이 기간의 이중 인프라 비용이 약 4.5억원으로 추정됩니다.",
                    "recommendation": "이중 운영 기간을 최소화하기 위해 "
                    "모듈별 전환 완료 즉시 온프레미스 자원을 해제하는 계획을 수립하십시오.",
                }
            )

        high_count = sum(1 for f in findings if f["severity"] == "높음")
        overall = "조건부 승인"

        result = {
            "agent": "비용 리뷰 에이전트",
            "verdict": overall,
            "high_severity_count": high_count,
            "findings": findings,
            "summary": "비용 관점에서 Oracle 라이선스 절감은 긍정적이나, "
            "3년 TCO 비교 없이 예산을 확정하는 것은 위험합니다. "
            "이중 운영 기간의 추가 비용과 예비비를 반영한 수정 예산안이 필요합니다.",
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
        proposed = proposal.get("proposed_changes", {})

        # 1) 팀 역량 분석
        findings.append(
            {
                "category": "팀 역량",
                "severity": "높음",
                "finding": "현재 운영팀은 온프레미스(물리 서버, WebLogic) 환경에 특화되어 있으며, "
                "Kubernetes/EKS 운영 경험이 부재합니다. "
                "컨테이너 오케스트레이션, 서비스 메시, IaC(Terraform) 역량이 "
                "전환 전에 확보되어야 합니다.",
                "recommendation": "전환 착수 3개월 전부터 운영팀 대상 EKS/Kubernetes 교육을 "
                "실시하고, 최소 2명의 CKA(Certified Kubernetes Administrator) "
                "인증 취득을 목표로 설정하십시오.",
            }
        )

        # 2) 모니터링 체계
        findings.append(
            {
                "category": "모니터링",
                "severity": "중간",
                "finding": "마이크로서비스 전환 시 모니터링 복잡도가 기하급수적으로 증가합니다. "
                "현재 단일 모놀리식 애플리케이션 대비 관찰해야 할 지표가 10배 이상 증가하며, "
                "분산 트레이싱 체계가 필수입니다.",
                "recommendation": "CloudWatch, Prometheus, Grafana 기반의 통합 모니터링 스택과 "
                "AWS X-Ray 기반 분산 트레이싱을 설계에 포함하십시오.",
            }
        )

        # 3) 장애 대응
        if "장애 복구" in str(proposal.get("expected_benefits", [])):
            findings.append(
                {
                    "category": "장애 대응",
                    "severity": "중간",
                    "finding": "장애 복구 시간 15분 목표는 클라우드 환경에서 달성 가능하나, "
                    "이를 위해서는 자동화된 장애 감지와 셀프 힐링(self-healing) 체계, "
                    "그리고 정기적인 카오스 엔지니어링 훈련이 전제되어야 합니다.",
                    "recommendation": "런북(Runbook)을 자동화하고, "
                    "분기별 장애 복구 훈련(DR Drill)을 실시하십시오.",
                }
            )

        # 4) 인력 감축 리스크
        if "인프라 운영 인력" in str(proposal.get("expected_benefits", [])):
            findings.append(
                {
                    "category": "인력 운영",
                    "severity": "높음",
                    "finding": "운영 인력 5명에서 2명으로 감축하는 계획은 비현실적입니다. "
                    "클라우드 전환 초기(최소 12개월)에는 온프레미스 전문가와 "
                    "클라우드 전문가가 모두 필요하며, 오히려 인력이 일시적으로 증가합니다.",
                    "recommendation": "전환 완료 후 6개월까지는 현재 인력을 유지하고, "
                    "클라우드 네이티브 역량 전환 후 단계적으로 조정하십시오. "
                    "기존 인력의 재교육(reskilling)을 우선 검토하십시오.",
                }
            )

        high_count = sum(1 for f in findings if f["severity"] == "높음")
        overall = "반려"

        result = {
            "agent": "운영 리뷰 에이전트",
            "verdict": overall,
            "high_severity_count": high_count,
            "findings": findings,
            "summary": "운영 관점에서 현재 팀의 클라우드 역량 부재와 "
            "비현실적인 인력 감축 계획이 가장 큰 리스크입니다. "
            "기술 전환 전에 조직 역량 전환이 선행되어야 하며, "
            "최소 3개월의 교육 기간을 프로젝트 일정에 추가할 것을 권고합니다.",
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
