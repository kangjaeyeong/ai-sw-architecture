"""
베이스 리뷰 에이전트
==================
LLM 기반 분석과 규칙 기반 폴백을 모두 지원하는 공통 베이스 클래스입니다.

- OPENAI_API_KEY가 설정되어 있으면 LLM 모드로 동작합니다.
- API 키가 없으면 규칙 기반 폴백으로 동작합니다.
"""

import json
import os

from openai import OpenAI
from python_a2a import A2AServer, Message, MessageRole, TextContent


# LLM에게 반환 형식을 지시하는 공통 프롬프트
RESPONSE_FORMAT_INSTRUCTION = """
반드시 아래 JSON 형식으로만 응답하십시오. 다른 텍스트를 포함하지 마십시오.

{
  "agent": "<에이전트 이름>",
  "verdict": "<승인 | 조건부 승인 | 반려>",
  "high_severity_count": <높음 심각도 건수>,
  "findings": [
    {
      "category": "<분석 항목>",
      "severity": "<높음 | 중간 | 낮음>",
      "finding": "<발견 사항 설명>",
      "recommendation": "<권고 사항>"
    }
  ],
  "summary": "<종합 의견 1~2문장>"
}

판정 기준:
- 높은 심각도가 2건 이상이면 "반려"
- 높은 심각도가 1건이면 "조건부 승인"
- 높은 심각도가 0건이면 "승인"
"""


class BaseReviewAgent(A2AServer):
    """LLM/규칙 기반 하이브리드 리뷰 에이전트 베이스 클래스"""

    # 서브클래스에서 반드시 정의
    agent_name: str = ""
    system_prompt: str = ""
    model: str = "gpt-5-mini"

    def __init__(self, agent_card):
        super().__init__(agent_card)
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self._openai = OpenAI(api_key=api_key)
            self._use_llm = True
        else:
            self._openai = None
            self._use_llm = False

    def handle_message(self, message):
        """A2A 메시지를 받아 리뷰 결과를 반환합니다."""
        try:
            proposal_text = (
                message.content.text
                if hasattr(message.content, "text")
                else str(message.content)
            )
            proposal = self._parse_proposal(proposal_text)

            if self._use_llm:
                result = self._analyze_with_llm(proposal_text)
            else:
                result = self.analyze_rule_based(proposal)

            return Message(
                role=MessageRole.AGENT,
                content=TextContent(text=json.dumps(result, ensure_ascii=False)),
            )
        except Exception as e:
            error_result = {
                "agent": self.agent_name,
                "verdict": "오류",
                "high_severity_count": 0,
                "findings": [],
                "summary": f"분석 중 오류 발생: {e}",
            }
            return Message(
                role=MessageRole.AGENT,
                content=TextContent(text=json.dumps(error_result, ensure_ascii=False)),
            )

    def _analyze_with_llm(self, proposal_text: str) -> dict:
        """LLM으로 제안서를 분석합니다."""
        full_prompt = self.system_prompt + "\n\n" + RESPONSE_FORMAT_INSTRUCTION

        try:
            response = self._openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": full_prompt},
                    {"role": "user", "content": f"아래 설계 제안서를 리뷰하십시오.\n\n{proposal_text}"},
                ],
                max_completion_tokens=16384,
            )

            raw = response.choices[0].message.content.strip()
            # JSON 블록 추출 (```json ... ``` 감싸는 경우 처리)
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            result = json.loads(raw)
            print(f"  [{self.agent_name}] LLM 분석 완료 (model={self.model})")
            return result
        except Exception as e:
            # LLM 호출 또는 파싱 실패 시 규칙 기반 폴백
            print(f"  [{self.agent_name}] LLM 폴백: {type(e).__name__}: {e}")
            return self.analyze_rule_based(self._parse_proposal(proposal_text))

    def analyze_rule_based(self, proposal: dict) -> dict:
        """규칙 기반 분석 (서브클래스에서 구현)"""
        raise NotImplementedError

    def _parse_proposal(self, text: str) -> dict:
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return {}
