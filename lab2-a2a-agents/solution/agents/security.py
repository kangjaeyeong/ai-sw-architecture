"""보안 리뷰 에이전트 — 데이터 주권, 암호화, 접근제어, 컴플라이언스"""

from .base import BaseReviewAgent


class SecurityReviewAgent(BaseReviewAgent):
    agent_name = "보안 리뷰 에이전트"
    system_prompt = """당신은 기업 아키텍처 심의위원회(ARB)의 보안 전문가입니다.
설계 제안서를 보안 관점에서 리뷰하고 발견 사항을 보고합니다.

분석 영역:
- 데이터 주권: 개인정보보호법, 데이터 3법, 국내 데이터 저장 의무
- 암호화: 저장 시 암호화(AES-256), 전송 중 암호화(TLS 1.3), 키 관리(KMS)
- 접근제어: RBAC, Pod Security Standards, NetworkPolicy
- 컴플라이언스: ISMS-P 인증 범위 변경, CSA STAR

분석 시 유의사항:
- 제안서에 보안 대책이 이미 포함되어 있다면 긍정적으로 평가하십시오.
- 구체적인 기술/정책이 명시되어 있으면 심각도를 낮추십시오.
- 데이터 분류 체계, 암호화 전략, 리전 정책이 명시되어 있으면 해당 항목은 "낮음"으로 평가하십시오.
"""

    def analyze_rule_based(self, proposal: dict) -> dict:
        findings = []
        proposed = proposal.get("proposed_changes", {})
        security = proposed.get("security_measures", {})

        # 데이터 주권
        if proposed.get("target_cloud") == "AWS":
            if security.get("data_residency"):
                findings.append({
                    "category": "데이터 주권",
                    "severity": "낮음",
                    "finding": "AWS 서울 리전 전용 정책과 데이터 분류 체계가 명시되어 있습니다.",
                    "recommendation": "설계 단계에서 데이터 흐름도를 작성하여 국외 전송 여부를 최종 확인하십시오.",
                })
            else:
                findings.append({
                    "category": "데이터 주권",
                    "severity": "높음",
                    "finding": "퍼블릭 클라우드 전환 시 개인정보보호법 및 데이터 3법에 따른 국내 데이터 저장 의무 검토가 필요합니다.",
                    "recommendation": "데이터 분류 체계를 수립하고, 민감 데이터는 국내 리전에만 저장하는 정책을 확정하십시오.",
                })

        # 암호화
        if "Oracle" in proposal.get("current_system", {}).get("stack", ""):
            if security.get("encryption"):
                findings.append({
                    "category": "암호화",
                    "severity": "낮음",
                    "finding": "KMS 기반 키 관리와 TLS 1.3, AES-256 암호화 전략이 수립되어 있습니다.",
                    "recommendation": "전환 과정에서 암호화 키 마이그레이션 절차를 테스트하십시오.",
                })
            else:
                findings.append({
                    "category": "암호화",
                    "severity": "높음",
                    "finding": "Oracle DB에서 Aurora PostgreSQL 전환 시 기존 TDE 설정이 유실될 수 있습니다.",
                    "recommendation": "AWS KMS 기반 암호화 키 관리를 도입하고, TLS 1.3과 AES-256을 적용하십시오.",
                })

        # 접근제어
        if "EKS" in proposed.get("architecture", ""):
            if security.get("access_control"):
                findings.append({
                    "category": "접근제어",
                    "severity": "낮음",
                    "finding": "PSS Restricted 프로파일과 NetworkPolicy 설계가 포함되어 있습니다.",
                    "recommendation": "네임스페이스별 정책을 정기적으로 감사하십시오.",
                })
            else:
                findings.append({
                    "category": "접근제어",
                    "severity": "중간",
                    "finding": "EKS 클러스터의 RBAC 설정이 명시되어 있지 않습니다.",
                    "recommendation": "Pod Security Standards Restricted 프로파일과 NetworkPolicy를 설계하십시오.",
                })

        # 컴플라이언스
        findings.append({
            "category": "컴플라이언스",
            "severity": "중간" if not security else "낮음",
            "finding": "클라우드 전환 시 ISMS-P 인증 범위 변경 신고가 필요합니다.",
            "recommendation": "ISMS-P 인증 기관에 범위 변경을 사전 협의하십시오.",
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
            "summary": f"보안 관점에서 {len(findings)}건의 검토 의견이 있으며, "
            f"이 중 {high_count}건이 높은 심각도입니다.",
        }
