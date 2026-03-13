"""운영 리뷰 에이전트 — 팀 역량, 모니터링, 장애 대응, 인력 운영"""

from .base import BaseReviewAgent


class OpsReviewAgent(BaseReviewAgent):
    agent_name = "운영 리뷰 에이전트"
    system_prompt = """당신은 기업 아키텍처 심의위원회(ARB)의 운영 전문가입니다.
설계 제안서를 운영 관점에서 리뷰하고 발견 사항을 보고합니다.

분석 영역:
- 팀 역량: 클라우드/K8s 운영 경험, CKA 인증, IaC(Terraform) 역량
- 모니터링: 통합 모니터링 스택, 분산 트레이싱, 알람 체계
- 장애 대응: 셀프 힐링, 런북 자동화, DR Drill, 카오스 엔지니어링
- 인력 운영: 인력 감축 계획의 현실성, 재교육(reskilling) 계획

분석 시 유의사항:
- 교육 계획과 CKA 인증 목표가 명시되어 있으면 팀 역량 항목 심각도를 낮추십시오.
- 인력 감축이 단계적이고 재교육 계획이 있으면 인력 운영을 "중간" 이하로 평가하십시오.
- 모니터링 스택이 구체적으로 명시되어 있으면 해당 항목은 "낮음"으로 평가하십시오.
"""

    def analyze_rule_based(self, proposal: dict) -> dict:
        findings = []
        proposed = proposal.get("proposed_changes", {})
        ops_plan = proposed.get("ops_plan", {})

        # 팀 역량
        if ops_plan.get("training"):
            findings.append({
                "category": "팀 역량",
                "severity": "중간",
                "finding": "EKS/Kubernetes 교육 계획이 포함되어 있으나, 실제 운영 경험 확보까지 시간이 필요합니다.",
                "recommendation": "교육 완료 후 스테이징 환경에서 최소 1개월간 운영 실습을 실시하십시오.",
            })
        else:
            findings.append({
                "category": "팀 역량",
                "severity": "높음",
                "finding": "현재 운영팀은 온프레미스 환경에 특화되어 있으며, K8s/EKS 운영 경험이 부재합니다.",
                "recommendation": "전환 착수 3개월 전부터 EKS/Kubernetes 교육을 실시하고, CKA 인증 취득을 목표로 설정하십시오.",
            })

        # 모니터링
        if ops_plan.get("monitoring"):
            findings.append({
                "category": "모니터링",
                "severity": "낮음",
                "finding": "CloudWatch, Prometheus, Grafana 기반 통합 모니터링과 분산 트레이싱이 계획되어 있습니다.",
                "recommendation": "알람 임계값을 서비스별로 정의하고 온콜 체계를 수립하십시오.",
            })
        else:
            findings.append({
                "category": "모니터링",
                "severity": "중간",
                "finding": "마이크로서비스 전환 시 모니터링 복잡도가 기하급수적으로 증가합니다.",
                "recommendation": "CloudWatch, Prometheus, Grafana 기반 통합 모니터링과 분산 트레이싱을 설계에 포함하십시오.",
            })

        # 장애 대응
        if "장애 복구" in str(proposal.get("expected_benefits", [])):
            findings.append({
                "category": "장애 대응",
                "severity": "중간" if ops_plan.get("dr_drill") else "중간",
                "finding": "장애 복구 시간 15분 목표는 자동화된 장애 감지와 셀프 힐링이 전제되어야 합니다.",
                "recommendation": "런북을 자동화하고 분기별 DR Drill을 실시하십시오.",
            })

        # 인력 감축 리스크
        benefits = str(proposal.get("expected_benefits", []))
        if "인력" in benefits or "인프라 운영 인력" in benefits:
            if ops_plan.get("reskilling"):
                findings.append({
                    "category": "인력 운영",
                    "severity": "중간",
                    "finding": "재교육 계획과 단계적 인력 조정이 포함되어 있으나, 전환 초기 이중 인력 운영은 불가피합니다.",
                    "recommendation": "전환 완료 후 6개월간 인력 유지 후 단계적으로 조정하십시오.",
                })
            else:
                findings.append({
                    "category": "인력 운영",
                    "severity": "높음",
                    "finding": "운영 인력 대폭 감축 계획은 비현실적입니다. 전환 초기에는 오히려 인력이 증가합니다.",
                    "recommendation": "기존 인력의 재교육(reskilling)을 우선 검토하고, 전환 완료 후 단계적으로 조정하십시오.",
                })

        high_count = sum(1 for f in findings if f["severity"] == "높음")
        if high_count >= 2:
            verdict = "반려"
        elif high_count == 1:
            verdict = "조건부 승인"
        else:
            verdict = "승인"

        return {
            "agent": self.agent_name,
            "verdict": verdict,
            "high_severity_count": high_count,
            "findings": findings,
            "summary": f"운영 관점에서 {len(findings)}건의 검토 의견이 있으며, "
            f"이 중 {high_count}건이 높은 심각도입니다.",
        }
