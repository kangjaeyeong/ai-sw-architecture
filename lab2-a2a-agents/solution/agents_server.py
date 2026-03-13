"""
아키텍처 심의위원회(ARB) — 에이전트 서버
=========================================
4개 전문가 에이전트를 일괄 실행합니다.

- OPENAI_API_KEY가 설정되어 있으면 LLM 기반 분석
- API 키가 없으면 규칙 기반 폴백

실행:
  uv run python solution/agents_server.py
"""

import os
import threading

from dotenv import load_dotenv
from python_a2a import AgentCard, run_server

from agents import (
    CostReviewAgent,
    OpsReviewAgent,
    PerformanceReviewAgent,
    SecurityReviewAgent,
)

load_dotenv()

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
    mode = "LLM" if os.getenv("OPENAI_API_KEY") else "규칙 기반"

    print("=" * 60)
    print("  아키텍처 심의위원회(ARB) — 전문가 에이전트 시작")
    print(f"  분석 모드: {mode}")
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
