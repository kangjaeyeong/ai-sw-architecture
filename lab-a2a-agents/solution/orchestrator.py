"""
아키텍처 심의위원회(ARB) — 오케스트레이터
==========================================
AgentCard 기반 동적 탐색으로 전문가 에이전트를 발견하고,
설계 제안서 리뷰를 수집하여 종합 심의 보고서를 생성합니다.

핵심 포인트:
  - 오케스트레이터는 에이전트 목록을 하드코딩하지 않습니다.
  - 지정된 포트 범위를 스캔하여 A2A AgentCard를 가진 서버를 자동 발견합니다.
  - 새 에이전트를 추가하려면 해당 포트에서 서버를 실행하기만 하면 됩니다.

실행:
  uv run python solution/orchestrator.py                                     # v1 심의
  uv run python solution/orchestrator.py --proposal design_proposal_v2.json  # v2 재심의
  uv run python solution/orchestrator.py --ports 5001-5010                   # 포트 범위 지정
"""

import argparse
import json
import sys
import time
from pathlib import Path

import requests
from python_a2a import A2AClient, Message, MessageRole, TextContent
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.tree import Tree

console = Console()


# ============================================================
# 에이전트 동적 발견 (AgentCard 기반)
# ============================================================
def discover_agents(port_start: int = 5001, port_end: int = 5004) -> list[dict]:
    """포트 범위를 스캔하여 A2A AgentCard를 가진 에이전트를 발견합니다.

    이것이 A2A 프로토콜의 핵심 차별점입니다.
    오케스트레이터는 에이전트 목록을 하드코딩하지 않고,
    AgentCard(/.well-known/agent.json)를 통해 런타임에 에이전트를 발견합니다.
    새 에이전트를 추가하려면 해당 포트에서 서버를 실행하기만 하면 됩니다.
    """
    agents = []
    for port in range(port_start, port_end + 1):
        url = f"http://localhost:{port}"
        try:
            resp = requests.get(f"{url}/.well-known/agent.json", timeout=1)
            if resp.status_code == 200:
                card = resp.json()
                agents.append({
                    "name": card.get("name", f"Agent:{port}"),
                    "description": card.get("description", ""),
                    "url": url,
                    "icon": f"[{card.get('name', str(port)).split()[0]}]",
                })
        except requests.ConnectionError:
            pass
        except Exception:
            pass
    return agents


# ============================================================
# 설계 제안서 로드
# ============================================================
def load_proposal(filename: str = "design_proposal.json"):
    """설계 제안서를 로드합니다."""
    proposal_path = Path(__file__).parent.parent / "data" / filename
    if not proposal_path.exists():
        console.print(f"[bold red]오류: 설계 제안서를 찾을 수 없습니다: {proposal_path}[/bold red]")
        sys.exit(1)

    with open(proposal_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# 에이전트 리뷰 수집
# ============================================================
def _review_single_agent(agent_info, proposal_text):
    """단일 에이전트에게 리뷰를 요청합니다 (병렬 실행용)."""
    try:
        client = A2AClient(agent_info["url"])
        message = Message(
            role=MessageRole.USER,
            content=TextContent(text=proposal_text),
        )

        start_time = time.time()
        response = client.send_message(message)
        elapsed = time.time() - start_time

        response_text = None
        if hasattr(response, "content") and response.content:
            response_text = response.content.text

        if response_text:
            review = json.loads(response_text)
            # 필수 필드 검증
            if "verdict" not in review:
                review["verdict"] = "오류"
            if "findings" not in review:
                review["findings"] = []
            if "agent" not in review:
                review["agent"] = agent_info.get("name", "알 수 없음")
            return {"review": review, "elapsed": elapsed}
    except Exception as e:
        return {"error": str(e)}
    return {"error": "응답 파싱 실패"}


def collect_reviews(proposal, agents):
    """발견된 에이전트에게 설계안을 병렬 전송하고 리뷰를 수집합니다."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    proposal_text = json.dumps(proposal, ensure_ascii=False)
    reviews = []

    console.print(f"\n  {len(agents)}명의 전문가에게 동시에 리뷰를 요청합니다...")

    futures = {}
    with ThreadPoolExecutor(max_workers=len(agents)) as executor:
        for i, agent_info in enumerate(agents):
            future = executor.submit(_review_single_agent, agent_info, proposal_text)
            futures[future] = (i, agent_info)

        for future in as_completed(futures):
            i, agent_info = futures[future]
            result = future.result()

            if "review" in result:
                review = result["review"]
                reviews.append(review)
                verdict = review["verdict"]
                if verdict == "반려":
                    verdict_style = "red"
                elif verdict == "조건부 승인":
                    verdict_style = "yellow"
                else:
                    verdict_style = "green"
                console.print(
                    f"  [bold]{agent_info['icon']}[/bold] {agent_info['name']}: "
                    f"[{verdict_style}]{verdict}[/{verdict_style}] "
                    f"({result['elapsed']:.1f}초)"
                )
            else:
                console.print(f"  [red]{agent_info['icon']} 실패: {result['error']}[/red]")

    return reviews


# ============================================================
# 충돌 분석
# ============================================================
def analyze_conflicts(reviews):
    """에이전트 간 상충하는 의견을 식별합니다."""
    conflicts = []

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
        verdict_style = "red"
    elif reject_count >= 1 or conditional_count >= 3:
        final_verdict = "조건부 승인 (수정 후 재심의)"
        verdict_style = "yellow"
    else:
        final_verdict = "승인"
        verdict_style = "green"

    # 전체 findings 심각도 집계
    all_findings = []
    for r in reviews:
        all_findings.extend(r["findings"])

    high = sum(1 for f in all_findings if f["severity"] == "높음")
    medium = sum(1 for f in all_findings if f["severity"] == "중간")
    low = sum(1 for f in all_findings if f["severity"] == "낮음")

    # ---- 출력 ----
    console.print()
    console.print(Panel(
        "아키텍처 심의위원회(ARB) 종합 보고서",
        border_style="bright_blue",
        padding=(1, 2),
    ))

    # 1. 심의 대상
    console.print(Rule("[bold]1. 심의 대상[/bold]", style="blue"))
    console.print(Panel(
        f"[bold]제목[/bold]: {proposal['title']}\n"
        f"[bold]제안 부서[/bold]: {proposal['proposer']}\n"
        f"[bold]제안 일자[/bold]: {proposal['date']}\n"
        f"[bold]핵심 내용[/bold]: {proposal['summary']}",
        border_style="blue",
    ))

    # 2. 전문가별 판정
    console.print(Rule("[bold]2. 전문가별 판정[/bold]", style="blue"))
    verdict_table = Table(show_header=True, header_style="bold")
    verdict_table.add_column("에이전트", style="bold")
    verdict_table.add_column("판정")
    verdict_table.add_column("요약")

    for review in reviews:
        v = review["verdict"]
        if v == "반려":
            v_display = f"[red]{v}[/red]"
        elif v == "조건부 승인":
            v_display = f"[yellow]{v}[/yellow]"
        else:
            v_display = f"[green]{v}[/green]"
        verdict_table.add_row(review["agent"], v_display, review["summary"])

    console.print(verdict_table)

    # 3. 높은 심각도 발견 사항
    console.print(Rule("[bold]3. 높은 심각도 발견 사항[/bold]", style="red"))
    tree = Tree("[bold red]높은 심각도[/bold red]")
    for review in reviews:
        high_findings = [f for f in review["findings"] if f["severity"] == "높음"]
        if high_findings:
            agent_branch = tree.add(f"[bold]{review['agent']}[/bold]")
            for finding in high_findings:
                node = agent_branch.add(f"[bold red][높음][/bold red] [bold]{finding['category']}[/bold]")
                node.add(f"발견: {finding['finding']}")
                node.add(f"[cyan]권고: {finding['recommendation']}[/cyan]")
    console.print(tree)

    # 4. 관점 충돌 분석
    if conflicts:
        console.print(Rule("[bold]4. 관점 충돌 분석[/bold]", style="yellow"))
        for i, conflict in enumerate(conflicts, 1):
            console.print(Panel(
                f"[bold]충돌[/bold]: {conflict['description']}\n"
                f"[cyan][bold]해결 방안[/bold]: {conflict['resolution']}[/cyan]",
                title=f"{i}. {conflict['type']}",
                border_style="yellow",
            ))

    # 5. 검토 통계
    console.print(Rule("[bold]5. 검토 통계[/bold]", style="blue"))
    console.print(f"  총 발견 사항: {len(all_findings)}건")
    console.print(
        f"    [red]높음: {high}건[/red]  "
        f"[yellow]중간: {medium}건[/yellow]  "
        f"[green]낮음: {low}건[/green]"
    )
    console.print(f"  관점 충돌: {len(conflicts)}건")

    # 최종 판정
    console.print()
    console.print(Panel(
        f"[bold {verdict_style}]최종 판정: {final_verdict}[/bold {verdict_style}]",
        border_style=verdict_style,
        padding=(1, 2),
    ))

    # 선행 조건 (조건부 승인인 경우)
    if "조건부" in final_verdict or final_verdict == "반려":
        console.print(Rule("[bold]6. 재심의 선행 조건[/bold]", style="cyan"))
        conditions = []
        for review in reviews:
            for finding in review["findings"]:
                if finding["severity"] == "높음":
                    conditions.append(
                        f"[{review['agent']}] {finding['recommendation']}"
                    )

        for i, cond in enumerate(conditions, 1):
            console.print(f"  {i}. {cond}")

        console.print()
        console.print("  [bold]위 조건을 충족한 후 재심의를 요청하십시오.[/bold]")

    console.print()


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
    parser.add_argument(
        "--ports",
        default="5001-5004",
        help="에이전트 탐색 포트 범위 (기본: 5001-5004)",
    )
    args = parser.parse_args()

    port_start, port_end = (int(p) for p in args.ports.split("-"))

    # 1. 설계 제안서 로드
    console.print(Panel(
        "아키텍처 심의위원회(ARB) 시작",
        border_style="bright_blue",
        padding=(1, 2),
    ))
    console.print(f"\n  설계 제안서를 로드합니다... ({args.proposal})")
    proposal = load_proposal(args.proposal)
    console.print(f"  제안: [bold]{proposal['title']}[/bold]")
    console.print(f"  예산: {proposal['proposed_changes']['budget']}")
    console.print(f"  기간: {proposal['proposed_changes']['timeline']}")

    # 2. 에이전트 동적 발견 (AgentCard 기반)
    console.print(Rule("[bold]에이전트 탐색 (AgentCard Discovery)[/bold]", style="cyan"))
    console.print(f"  포트 {port_start}~{port_end} 범위에서 A2A 에이전트를 탐색합니다...")

    agents = discover_agents(port_start, port_end)

    if not agents:
        console.print(
            "\n[bold red]오류: 발견된 에이전트가 없습니다. "
            "agents_server.py가 실행 중인지 확인하십시오.[/bold red]"
        )
        sys.exit(1)

    agent_table = Table(show_header=True, header_style="bold")
    agent_table.add_column("에이전트")
    agent_table.add_column("URL")
    agent_table.add_column("설명")
    for agent in agents:
        agent_table.add_row(agent["name"], agent["url"], agent["description"])
    console.print(agent_table)

    console.print(f"\n  [green]{len(agents)}개의 전문가 에이전트를 발견했습니다.[/green]")

    # 3. 전문가 에이전트에게 병렬 리뷰 요청
    console.print(Rule("[bold]전문가 리뷰 수집 (병렬)[/bold]", style="cyan"))
    reviews = collect_reviews(proposal, agents)

    if not reviews:
        console.print("\n[bold red]오류: 수집된 리뷰가 없습니다.[/bold red]")
        sys.exit(1)

    console.print(f"\n  [green]{len(reviews)}명의 전문가로부터 리뷰를 수집했습니다.[/green]")

    # 3. 관점 충돌 분석
    console.print(Rule("[bold]관점 충돌 분석 중...[/bold]", style="yellow"))
    conflicts = analyze_conflicts(reviews)
    console.print(f"  {len(conflicts)}건의 관점 충돌을 식별했습니다.")

    # 4. 종합 보고서 생성
    generate_final_report(proposal, reviews, conflicts)


if __name__ == "__main__":
    main()
