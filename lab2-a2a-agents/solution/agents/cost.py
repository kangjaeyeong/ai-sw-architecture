"""비용 리뷰 에이전트 — TCO, 라이선스, 예비비, 이중 운영 비용"""

from .base import BaseReviewAgent


class CostReviewAgent(BaseReviewAgent):
    agent_name = "비용 리뷰 에이전트"
    system_prompt = """당신은 기업 아키텍처 심의위원회(ARB)의 비용 전문가입니다.
설계 제안서를 비용 관점에서 리뷰하고 발견 사항을 보고합니다.

분석 영역:
- 총 소유 비용(TCO): 마이그레이션 비용, 3~5년 운영비, 온프레미스 대비 비교
- 라이선스: Oracle 라이선스 해지 절감, 잔여 계약 위약금
- 예비비: 프로젝트 예비비(contingency) 15% 확보 여부
- 이중 운영 비용: 전환 기간 동안 온프레미스/클라우드 동시 운영 비용

분석 시 유의사항:
- TCO 비교표가 제안서에 포함되어 있으면 해당 항목 심각도를 낮추십시오.
- 예비비가 명시되어 있으면 해당 항목은 "낮음"으로 평가하십시오.
- 비용 최적화 전략(RI, Spot, Savings Plans)이 있으면 긍정적으로 평가하십시오.
"""

    def analyze_rule_based(self, proposal: dict) -> dict:
        findings = []
        proposed = proposal.get("proposed_changes", {})
        budget_plan = proposed.get("budget_plan", {})

        # TCO
        if budget_plan.get("tco_comparison"):
            findings.append({
                "category": "총 소유 비용(TCO)",
                "severity": "낮음",
                "finding": "5년 TCO 비교표가 제출되어 있으며, 비용 최적화 전략이 포함되어 있습니다.",
                "recommendation": "분기별 비용 리뷰를 실시하여 예산 대비 실적을 추적하십시오.",
            })
        else:
            budget = proposed.get("budget", "")
            findings.append({
                "category": "총 소유 비용(TCO)",
                "severity": "높음",
                "finding": f"제안된 예산 {budget}은 마이그레이션 비용만 포함한 것으로 보입니다. "
                "3년 TCO 비교 없이 예산을 확정하는 것은 위험합니다.",
                "recommendation": "온프레미스 유지 시나리오와 클라우드 전환 시나리오의 5년 TCO 비교표를 작성하십시오.",
            })

        # 라이선스
        if "Oracle" in proposal.get("current_system", {}).get("stack", ""):
            findings.append({
                "category": "라이선스",
                "severity": "낮음",
                "finding": "Oracle DB 라이선스 해지 시 연간 약 3억원의 비용 절감이 가능합니다.",
                "recommendation": "Oracle 라이선스 계약 잔여 기간과 위약금 발생 여부를 확인하십시오.",
            })

        # 예비비
        if budget_plan.get("contingency"):
            findings.append({
                "category": "예비비",
                "severity": "낮음",
                "finding": f"예비비 {budget_plan['contingency']}이 확보되어 있습니다.",
                "recommendation": "월별 비용 추적 체계를 수립하여 예비비 소진율을 관리하십시오.",
            })
        else:
            findings.append({
                "category": "예비비",
                "severity": "중간",
                "finding": "18개월 프로젝트에서 예비비(contingency)가 책정되어 있지 않습니다.",
                "recommendation": "전체 예산의 15%를 예비비로 별도 확보하십시오.",
            })

        # 이중 운영 비용
        if proposed.get("migration_strategy", "").startswith("Strangler"):
            findings.append({
                "category": "이중 운영 비용",
                "severity": "중간" if budget_plan.get("dual_operation") else "중간",
                "finding": "Strangler Fig 패턴 적용 시 전환 기간 동안 이중 인프라 비용이 발생합니다.",
                "recommendation": "모듈별 전환 완료 즉시 온프레미스 자원을 해제하는 계획을 수립하십시오.",
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
            "summary": f"비용 관점에서 {len(findings)}건의 검토 의견이 있으며, "
            f"이 중 {high_count}건이 높은 심각도입니다.",
        }
