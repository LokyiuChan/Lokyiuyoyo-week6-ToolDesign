# Tool Use Demo: Text Statistics + DeepSeek

A minimal **tool-use** demo: an LLM (DeepSeek, OpenAI-compatible API) decides when to call a custom **text statistics** tool, then synthesizes a natural-language response from the results.

---

## What the Tool Does

The project provides a single tool, **text_statistics**, in `tool.py`:

- **Input:** A string (`text`).
- **Output:** A JSON-serializable dict with:
  - **Success:** `word_count`, `sentence_count`, `avg_word_length`, `avg_sentence_length`, and a **readability_label** (`"Easy"`, `"Medium"`, or `"Hard"`).
  - **Failure:** `success: false`, `error` (message), and `error_code` (e.g. `invalid_input`, `empty_text`).

**Readability** is a simple heuristic: short sentences (≤15 words) and short words (≤5 chars) → Easy; long sentences (>20 words) or long words (>6 chars) → Hard; otherwise → Medium. Words are whitespace-split; sentences are split on `.` `!` `?`. Invalid or empty input returns a structured error dict instead of raising.

A **Tool** wrapper class exposes `execute(**kwargs)` and `to_dict()` for a function-calling style schema (name, description, parameters).

---

## How to Run the Demo

1. **Environment**
   - Create a virtual environment and install dependencies:
     ```bash
     python3 -m venv venv
     source venv/bin/activate   # Windows: venv\Scripts\activate
     pip install -r requirements.txt
     ```
   - Copy `.env.example` to `.env` in the project root and set your DeepSeek API key:
     ```bash
     cp .env.example .env
     ```
     Then edit `.env` and replace `your_deepseek_api_key_here` with your real API key. Optionally adjust `DEEPSEEK_API_BASE` and `DEEPSEEK_MODEL` if needed.

2. **Run**
   - Main demo (four runs: Easy text, Hard text, invalid type, empty text):
     ```bash
     python demo.py
     ```
   - Two-run variant (normal + invalid input):
     ```bash
     python demo-1.py
     ```

Output shows, for each run: which tool was called, the tool result (JSON), and the final LLM response.

---

## Design Decisions and Limitations

- **Single-tool, prompt-based tool use:** The LLM is instructed to respond with a strict JSON list of tool calls (e.g. `[{"tool":"text_statistics","args":{"text":"..."}}]`). The demo parses this, runs the tool in Python, then sends the result to a second LLM call for synthesis. No native API tool-calling (e.g. OpenAI function calling) is used.
- **Structured errors:** The tool and `Tool.execute()` always return a dict (success or error). Exceptions are caught and turned into a JSON-serializable error dict so the orchestrator and second LLM can handle failures consistently.
- **Limitations:** Readability is a heuristic, not a standard index (e.g. Flesch–Kincaid). Sentence splitting does not handle abbreviations (e.g. "Dr."). The demo depends on the first LLM returning valid JSON; malformed responses are treated as “no tool call.” API key and network are required for `demo.py` / `demo-1.py`.
