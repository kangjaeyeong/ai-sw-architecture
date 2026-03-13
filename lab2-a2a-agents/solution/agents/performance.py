"""성능 리뷰 에이전트 — 스케일링, DB 성능, 네트워크 레이턴시, 캐싱"""

from .base import BaseReviewAgent


class PerformanceReviewAgent(BaseReviewAgent):
    agent_name = "성능 리뷰 에이전트"
    system_prompt = """당신은 기업 아키텍처 심의위원회(ARB)의 성능 전문가입니다.
설계 제안서를 성능 관점에서 리뷰하고 발견 사항을 보고합니다.

분석 영역:
- 오토스케일링: HPA/VPA 설정, 스케일링 메트릭, 최대 Pod 수
- 데이터베이스 성능: DB 전환 시 쿼리 호환성, PL/SQL 프로시저, 동시 접속 SLA
- 네트워크 레이턴시: 마이크로서비스 간 호출 증가, 서비스 메시, gRPC
- 캐싱 전략: ElastiCache/Redis, 캐시 무효화, TTL 정책

분석 시 유의사항:
- 제안서에 쿼리 검증 계획, 성능 테스트 일정이 있으면 DB 성능 심각도를 낮추십시오.
- 캐싱 전략이 명시되어 있으면 해당 항목은 "낮음"으로 평가하십시오.
- 서비스 메시나 gRPC 도입 계획이 있으면 레이턴시 항목을 "낮음"으로 평가하십시오.
"""

    def analyze_rule_based(self, proposal: dict) -> dict:
        findings = []
        proposed = proposal.get("proposed_changes", {})
        perf = proposed.get("performance_plan", {})

        # 오토스케일링
        if "EKS" in proposed.get("architecture", ""):
            findings.append({
                "category": "오토스케일링",
                "severity": "낮음",
                "finding": "EKS 기반 컨테이너 아키텍처는 HPA/VPA를 통한 자동 스케일링이 가능합니다.",
                "recommendation": "HPA 메트릭 기준(CPU 70%, Memory 80%)과 최대 Pod 수를 사전에 정의하십시오.",
            })

        # DB 성능
        if "Aurora" in proposed.get("database", ""):
            if perf.get("query_validation"):
                findings.append({
                    "category": "데이터베이스 성능",
                    "severity": "중간",
                    "finding": "슬로우 쿼리 검증 계획이 포함되어 있으나, 전환 후 성능 회귀 테스트 일정이 필요합니다.",
                    "recommendation": "전환 후 1주간 성능 회귀 테스트를 실시하고 SLA 충족을 확인하십시오.",
                })
            else:
                findings.append({
                    "category": "데이터베이스 성능",
                    "severity": "높음",
                    "finding": "Oracle에서 PostgreSQL 전환 시 PL/SQL 프로시저, 힌트 기반 쿼리 차이로 20% 이상 성능 저하가 발생할 수 있습니다.",
                    "recommendation": "전환 전 상위 50개 슬로우 쿼리를 식별하여 PostgreSQL 호환성을 검증하십시오.",
                })

        # 네트워크 레이턴시
        if perf.get("service_mesh"):
            findings.append({
                "category": "네트워크 레이턴시",
                "severity": "낮음",
                "finding": "서비스 메시와 gRPC 도입 계획이 포함되어 레이턴시 대책이 수립되어 있습니다.",
                "recommendation": "핵심 경로의 레이턴시 버짓을 정의하고 정기 모니터링하십시오.",
            })
        else:
            findings.append({
                "category": "네트워크 레이턴시",
                "severity": "중간",
                "finding": "마이크로서비스 전환 시 서비스 간 호출 증가로 레이턴시가 30~50% 증가할 수 있습니다.",
                "recommendation": "서비스 메시(Istio)와 gRPC를 도입하고 레이턴시 버짓을 정의하십시오.",
            })

        # 캐싱
        if perf.get("caching"):
            findings.append({
                "category": "캐싱 전략",
                "severity": "낮음",
                "finding": "ElastiCache(Redis) 기반 캐싱 전략과 TTL 정책이 수립되어 있습니다.",
                "recommendation": "캐시 적중률을 모니터링하고 무효화 정책을 정기 검토하십시오.",
            })
        else:
            findings.append({
                "category": "캐싱 전략",
                "severity": "중간",
                "finding": "제안서에 캐싱 전략이 명시되어 있지 않습니다.",
                "recommendation": "읽기 빈도가 높은 API를 식별하고 캐시 TTL과 무효화 정책을 설계에 포함하십시오.",
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
            "summary": f"성능 관점에서 {len(findings)}건의 검토 의견이 있으며, "
            f"이 중 {high_count}건이 높은 심각도입니다.",
        }
