"""
MSA 시연 데모 스크립트

3개 서비스를 순차적으로 호출하여 파이프라인 동작을 시각적으로 보여줍니다.
서비스가 이미 실행 중이어야 합니다.

사용법:
  # 터미널 1, 2, 3에서 각각 서비스를 실행
  uv run python solution/intent_service.py   # 포트 8001
  uv run python solution/rag_service.py      # 포트 8002
  uv run python solution/orchestrator.py     # 포트 8000

  # 터미널 4에서 데모 실행
  uv run python solution/demo.py             # 대화형 모드
  uv run python solution/demo.py --demo      # 데모만 실행
  uv run python solution/demo.py "질문"      # 단일 질문
"""

import argparse

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.table import Table

console = Console()

ORCHESTRATOR_URL = "http://localhost:8000"

DEMO_QUESTIONS = [
    "재택근무 규정이 어떻게 되나요?",
    "VPN 접속하려면 어떻게 해야 하나요?",
    "경비 정산은 어디서 하나요?",
    "김민수 사원의 연차 잔여일이 궁금합니다",
]


def demo_single_question(question: str):
    """단일 질문에 대한 파이프라인 실행 과정을 시각화합니다."""
    console.print()
    console.print(Rule(f"[bold]{question}[/bold]", style="bright_white"))

    response = httpx.post(
        f"{ORCHESTRATOR_URL}/chat",
        json={"message": question},
        timeout=30.0,
    )

    if response.status_code != 200:
        console.print(
            f"[bold red]오류: {response.status_code} - {response.text}[/bold red]"
        )
        return

    data = response.json()

    # 파이프라인 단계별 결과 출력
    for step in data["pipeline"]:
        if step["step"] == "의도 분류":
            r = step["result"]
            content = (
                f"도메인: [bold]{r['domain']}[/bold]  "
                f"(신뢰도: {r['confidence']})\n"
                f"매칭 키워드: {r.get('matched_keywords', [])}"
            )
            console.print(
                Panel(content, title=f"[bold]의도 분류[/bold] ({step['service']})", border_style="cyan")
            )
        elif step["step"] == "RAG 검색":
            r = step["result"]
            table = Table(title=f"검색 결과: {r['total_found']}건", show_lines=False)
            table.add_column("ID", style="dim")
            table.add_column("제목")
            table.add_column("점수", justify="right")
            for doc in r.get("results", []):
                table.add_row(doc["id"], doc["title"], str(doc["score"]))
            console.print(
                Panel(table, title=f"[bold]RAG 검색[/bold] ({step['service']})", border_style="yellow")
            )
        elif step["step"] == "LLM 응답 생성":
            console.print(
                Panel(
                    "모델: OpenAI gpt-5-mini",
                    title=f"[bold]LLM 응답 생성[/bold] ({step['service']})",
                    border_style="green",
                )
            )

    console.print(
        Panel(data["answer"], title="답변", border_style="bold green", padding=(1, 2))
    )
    if data.get("sources"):
        console.print(f"  [dim]출처: {', '.join(data['sources'])}[/dim]")


def demo_health_check():
    """전체 서비스 상태를 확인합니다."""
    response = httpx.get(f"{ORCHESTRATOR_URL}/health", timeout=5.0)
    data = response.json()

    table = Table(title="서비스 상태")
    table.add_column("서비스", style="bold")
    table.add_column("포트", justify="center")
    table.add_column("상태", justify="center")

    orch_status = data["status"]
    table.add_row(
        "orchestrator",
        "8000",
        f"[green]{orch_status}[/green]" if orch_status == "healthy" else f"[red]{orch_status}[/red]",
    )
    for name, info in data.get("downstream", {}).items():
        port = "8001" if name == "intent" else "8002"
        status = info["status"]
        table.add_row(
            name,
            port,
            f"[green]{status}[/green]" if status == "healthy" else f"[red]{status}[/red]",
        )

    console.print(table)


def run_demo():
    """데모 질문을 순차 실행합니다."""
    for question in DEMO_QUESTIONS:
        try:
            demo_single_question(question)
        except httpx.ConnectError as e:
            console.print(f"[bold red]서비스 연결 실패: {e}[/bold red]")
    console.print()
    console.print("[bold]시연 완료[/bold]")


def interactive_loop():
    """대화형 질의 루프입니다."""
    console.print()
    console.print(Rule("대화형 모드", style="bright_blue"))
    console.print("[dim]질문을 입력하세요. quit/exit/q로 종료, demo로 데모 재실행[/dim]")
    console.print(
        "[dim]예: 재택근무 규정이 어떻게 되나요? / VPN 접속 방법 / 경비 정산[/dim]"
    )

    while True:
        console.print()
        user_input = Prompt.ask("[bold bright_blue]질문[/bold bright_blue]")
        stripped = user_input.strip()

        if not stripped:
            continue
        if stripped.lower() in ("quit", "exit", "q"):
            console.print("[dim]종료합니다.[/dim]")
            break
        if stripped.lower() == "demo":
            run_demo()
            continue

        try:
            demo_single_question(stripped)
        except httpx.ConnectError as e:
            console.print(f"[bold red]서비스 연결 실패: {e}[/bold red]")


def main():
    parser = argparse.ArgumentParser(description="MSA AI 어시스턴트 시연 데모")
    parser.add_argument("query", nargs="?", help="단일 질문 (생략 시 대화형 모드)")
    parser.add_argument(
        "--demo", action="store_true", help="데모 질문만 실행 (대화형 모드 없음)"
    )
    args = parser.parse_args()

    console.print(
        Panel(
            "MSA AI 어시스턴트 시연 데모\n"
            "[dim]서비스: 의도 분류(8001) + RAG 검색(8002) + 오케스트레이터(8000)[/dim]",
            border_style="bright_blue",
            padding=(1, 2),
        )
    )

    # 헬스 체크
    try:
        demo_health_check()
    except httpx.ConnectError:
        console.print(
            "[bold red]오케스트레이터에 연결할 수 없습니다.[/bold red]\n"
            "[bold red]3개 서비스를 먼저 실행하십시오.[/bold red]"
        )
        return

    if args.demo:
        run_demo()
    elif args.query:
        try:
            demo_single_question(args.query)
        except httpx.ConnectError as e:
            console.print(f"[bold red]서비스 연결 실패: {e}[/bold red]")
    else:
        interactive_loop()


if __name__ == "__main__":
    main()
