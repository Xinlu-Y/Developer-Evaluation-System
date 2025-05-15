from langsmith import Client
from config import OLLAMA_LLM
from typing import Dict
import json, re

client = Client()

prompt_template = """You are grading text summaries of larger source documents.

Ensure that the Assistant's Summary meets the following criteria: 
(1) it is factually accurate relative to the source document

Return your answer **as JSON on a single line, nothing else**:
{"score": <float_between_0_and_1>, "explanation": "<your_explanation>"}

* score must be a float between 0 and 1 (e.g., 0.0 means not accurate at all; 1.0 means fully accurate).
* Do NOT output any additional keys or text.

Explain your reasoning clearly and concisely.
"""

def parse_helpfulness_output(response: str) -> Dict[str, object]:
    """
    尝试解析 LLM 返回的 JSON 格式评分和解释，支持浮点数。
    """
    last = response.strip().splitlines()[-1]
    try:
        data = json.loads(last)
        score = float(data.get("score", data.get("Score", 0.0)))
        score = min(max(score, 0.0), 1.0)  # clamp 到 [0,1]
        explanation = data.get("explanation", data.get("Explanation", ""))
        return {"score": score, "explanation": explanation or "No explanation."}
    except Exception:
        pass

    score = None
    explanation = ""
    for line in response.splitlines():
        if line.lower().startswith("score"):
            m = re.search(r'(\d+(\.\d+)?)', line)
            score = float(m.group(1)) if m else None
        elif line.lower().startswith("explanation"):
            explanation = line.split(":", 1)[1].strip()

    return {"score": min(max(score, 0.0), 1.0) if isinstance(score, float) else 0.0,
            "explanation": explanation or "No explanation."}

def helpfulness(inputs: dict, outputs: dict) -> float:
    """
    对单个摘要打分，返回 0.0 ~ 1.0 的评分。
    """
    print("DEBUG type(outputs):", type(outputs))
    print("DEBUG outputs:", outputs[:200] if isinstance(outputs, str) else outputs)

    source = inputs.get("context", "")
    summary = outputs.get("summary", "")

    user_block = f"Assistant's Summary: {summary}\n\nSource document: {source}"
    full_prompt = prompt_template + "\n\n" + user_block

    try:
        raw = OLLAMA_LLM.invoke(full_prompt)
        # print("🔴 RAW LLM OUTPUT ↙︎\n", raw[:500])
        parsed = parse_helpfulness_output(raw)
        # print("🟢 PARSED ↙︎", parsed)

        score = float(parsed.get("score", 0.0))
        return round(score, 4)
    except Exception as e:
        print("helpfulness evaluator failed:", e)
        return 0.0

