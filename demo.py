"""
Tool-enabled demo: DeepSeek selects and calls text_statistics, then synthesizes a final response.
"""

import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from tool import text_statistics_tool

# Load .env and create DeepSeek-configured OpenAI client
load_dotenv()

api_key = os.getenv("DEEPSEEK_API_KEY")
base_url = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")
model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

client = OpenAI(api_key=api_key, base_url=base_url)

# Single tool from tool.py; use to_dict() for name, description, parameters
tool = text_statistics_tool
tool_schema = tool.to_dict()


def _tool_selection_prompt(user_task: str) -> str:
    """Build the prompt for the first LLM call (tool selection)."""
    return f"""You have access to one tool. Decide whether to use it for the user's task.

Tool:
- name: {tool_schema["name"]}
- description: {tool_schema["description"]}
- parameters: {json.dumps(tool_schema["parameters"])}

User task: {user_task}

Respond with a strict JSON list only, no other text:
- To use the tool: [{{"tool":"text_statistics","args":{{"text":"<the text to analyze>"}}}}]
- To skip: []

Examples:
- User asks to analyze a passage -> [{{"tool":"text_statistics","args":{{"text":"<the passage>"}}}}]
- User asks something unrelated -> []
"""


def _parse_tool_calls(response_text: str) -> list:
    """Parse LLM response into a list of tool calls. Return [] on invalid JSON or wrong shape."""
    text = response_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return parsed


def _run_tool_calls(tool_calls: list) -> list:
    """Execute each tool call and return a list of result dicts."""
    results = []
    for call in tool_calls:
        if not isinstance(call, dict):
            results.append({"success": False, "error": "Invalid tool call shape.", "error_code": "invalid_call"})
            continue
        name = call.get("tool") or call.get("name")
        args = call.get("args") or call.get("arguments") or {}
        if name != "text_statistics":
            results.append({"success": False, "error": f"Unknown tool: {name}", "error_code": "unknown_tool"})
            continue
        if not isinstance(args, dict):
            args = {}
        result = tool.execute(**args)
        results.append(result)
    return results


def _synthesis_prompt(user_task: str, tool_results: list) -> str:
    """Build the prompt for the second LLM call (final synthesis)."""
    results_str = json.dumps(tool_results, indent=2)
    return f"""The user asked: {user_task}

Tool results (from text_statistics if it was used):
{results_str}

Based on the task and the tool results above, write a short final response to the user. If the tool failed, explain the error in a friendly way. If it succeeded, summarize the statistics and readability in one to three sentences."""


def run_demo(user_task: str, tool_calls_override: list | None = None) -> None:
    """
    Run the full workflow: (optional) first LLM for tool selection -> execute tool(s) -> second LLM for synthesis.
    If tool_calls_override is provided, skip the first LLM and use that as the tool-calls list.
    """
    if tool_calls_override is not None:
        tool_calls = tool_calls_override
    else:
        prompt = _tool_selection_prompt(user_task)
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
            content = (resp.choices[0].message.content or "").strip()
        except Exception as e:
            print("[First LLM call failed]", e)
            content = "[]"
        tool_calls = _parse_tool_calls(content)

    tool_results = _run_tool_calls(tool_calls)

    if tool_results:
        print("[Tool called: text_statistics]")
        result = tool_results[0] if len(tool_results) == 1 else tool_results
        print("Tool result:", json.dumps(result, indent=2))
    else:
        print("[Tool called: none]")
        print("Tool result: []")

    synthesis_prompt = _synthesis_prompt(user_task, tool_results)
    try:
        resp2 = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": synthesis_prompt}],
        )
        final = (resp2.choices[0].message.content or "").strip()
    except Exception as e:
        final = f"[Second LLM call failed] {e}"
    print("[Final response]")
    print(final)
    print()


SAMPLE_NEWS_TEXT = (
    "The government announced a new policy on renewable energy today. "
    "Officials said the plan would create thousands of jobs and cut emissions. "
    "Critics argue the costs are too high. What do you think?"
)

HARD_TEXT = (
    "Internationalization, interdisciplinarity, and institutionalization are frequently "
    "characterized as indispensable prerequisites for the operationalization of "
    "comprehensive infrastructural modernization, notwithstanding the administrative "
    "heterogeneity and methodological complexities that stakeholders continuously "
    "problematize in policy deliberations."
)


def main() -> None:
    print("=" * 50)
    print("Run A: Normal input (Easy text)")
    print("=" * 50)
    run_demo(f"Analyze this text and tell me the statistics and readability:\n\n{SAMPLE_NEWS_TEXT}")

    print("=" * 50)
    print("Run B: Normal input (Hard text)")
    print("=" * 50)
    run_demo(f"Analyze this text and tell me the statistics and readability:\n\n{HARD_TEXT}")

    print("=" * 50)
    print("Run C: Bad Input (number)")
    print("=" * 50)
    run_demo(
        "Analyze this for text statistics: 123",
        tool_calls_override=[{"tool": "text_statistics", "args": {"text": 123}}],
    )

    print("=" * 50)
    print("Run D: Bad Input (Empty text)")
    print("=" * 50)
    run_demo(
        "Analyze this text:",
        tool_calls_override=[{"tool": "text_statistics", "args": {"text": ""}}],
    )


if __name__ == "__main__":
    main()
