"""
FP&A Copilot — orchestrator.
An LLM (via OpenRouter) acts as the router: given a natural-language request,
it decides which deterministic tool(s) in tools.py to call and with what
arguments. The LLM never does the financial judgment itself — that stays in
plain, auditable Python (see tools.py). This is the orchestrator-worker
pattern: one orchestrator call routes to workers; each worker's logic is
inspectable and testable independent of the LLM.

Usage:
    python orchestrator.py "What's the forecast for MNDY?"
    python orchestrator.py "Check this rec: net diff 11800, explained 11800, one item: vendor invoice posted twice for 11500, category duplicate"
"""
import json
import os
import sys

from openai import OpenAI

from tools import TOOL_SCHEMAS, TOOL_FUNCTIONS

MODEL = "openai/gpt-4o-mini"  # cheap, reliable tool-calling. Swap here to change cost/quality tradeoff.

SYSTEM_PROMPT = """You are an FP&A copilot orchestrator. You have three tools:
get_forecast, get_variance_commentary, and get_reconciliation_check. Each tool
does real financial judgment in deterministic Python code — you do not
calculate or judge anything yourself, you only decide which tool(s) to call
and extract the right arguments from the user's request. If the user's
request doesn't map to a tool, say so plainly rather than guessing an answer.
After tool results come back, summarize them for the user, but do not add
numbers or conclusions the tools didn't return — you are a router and
summarizer, not an independent analyst."""


def run_copilot(user_request: str) -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return ("ERROR: OPENROUTER_API_KEY not set in environment. "
                "This is a connection failure, not a code bug — set the key and retry.")

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_request},
    ]

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOL_SCHEMAS,
        tool_choice="auto",
    )

    message = response.choices[0].message

    if not message.tool_calls:
        # LLM decided no tool applies — return its plain response
        return message.content

    messages.append(message)
    _execute_tool_calls(message, messages)

    final_response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
    )

    return final_response.choices[0].message.content


def _execute_tool_calls(message, messages):
    """Run each tool the LLM requested and append its result as a tool message.
    Mutates `messages` in place (matches OpenAI's tool-call message-thread shape)."""
    for tool_call in message.tool_calls:
        fn_name = tool_call.function.name
        fn_args = json.loads(tool_call.function.arguments)

        if fn_name not in TOOL_FUNCTIONS:
            result = {"error": f"Unknown tool requested: {fn_name}"}
        else:
            try:
                result = TOOL_FUNCTIONS[fn_name](**fn_args)
            except Exception as e:
                result = {"error": f"Tool '{fn_name}' raised an exception: {e}"}

        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(result),
        })


if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "What's the forecast for MNDY?"
    print(f"USER: {query}\n")
    print("COPILOT:")
    print(run_copilot(query))
