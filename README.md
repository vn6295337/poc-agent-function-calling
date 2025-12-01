# poc-agent-function-calling

## Elevator pitch (3 lines)
Incident Triage Agent using structured function calling to extract severity, classify incident type, and recommend standard mitigations.  
Proves ability to design schemas, handle LLM → function → LLM loops, and maintain deterministic responses.  
Demonstrates agent reliability needed for production workflows in IT Ops and enterprise automation.

## What this proves (3 bullets)
- Clean JSON schema definitions consumed by Claude/OpenAI function calling.  
- Deterministic function execution loop with validated structured outputs.  
- Reusable agent UI (CLI or Streamlit) suitable for demos and interviews.

## Quick start
1. Install dependencies: `pip install -r requirements.txt`  
2. Fill out `.env` with `OPENAI_API_KEY` or `CLAUDE_API_KEY`.  
3. Run CLI agent: `python agent/cli_agent.py`  
4. Or launch UI: `streamlit run ui/app.py`

## Live demo
- Demo GIF: docs/demo.gif  
- Video walkthrough: _(optional)_

## Repo layout
- `agent/` — core agent loop, planning logic, LLM IO  
- `functions/` — function schemas + execution handlers  
- `ui/` — Streamlit interface  
- `tests/` — structured output validation tests  
- `docs/` — architecture, implementation notes, run instructions

## Tech stack
Python, OpenAI/Claude Function Calling, Streamlit (optional)

## License
MIT
