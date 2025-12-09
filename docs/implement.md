# Implementation Guide

## Development Timeline

**Total:** 5 days (21 hours), ~2,000 lines of code

- **Day 15 (4h):** Function schemas, handlers, LLM client
- **Day 16 (5h):** Agent core, execution loop, validation
- **Day 17 (4h):** CLI, Streamlit UI, testing
- **Day 18 (4h):** README, documentation
- **Day 19 (4h):** Deep documentation, case study

## Key Implementation Decisions

### 1. Function Calling Format Translation

**Challenge:** Gemini uses different format than OpenAI/Groq

**Solution:** Format conversion layer

```python
# OpenAI/Groq
{"tools": [{"type": "function", "function": {...}}]}

# Gemini  
{"tools": [{"functionDeclarations": [{...}]}]}
```

**Code:** llm_client.py:386-397

### 2. Conversation History Management

**Challenge:** OpenAI format requires proper message sequence

**Solution:** Explicit message construction

```python
messages = [
  {"role": "system", "content": "..."},
  {"role": "user", "content": "incident"},
  {"role": "assistant", "tool_calls": [...]},
  {"role": "tool", "tool_call_id": "...", "content": "result"},
  {"role": "assistant", "content": "summary"}
]
```

**Code:** core.py:136-157

### 3. Multi-Provider Fallback

**Challenge:** Rate limits on free tiers

**Solution:** Try-except cascade

```python
try:
    return gemini()
except:
    try:
        return groq()
    except:
        return openrouter()
```

**Code:** llm_client.py:88-116

### 4. Deterministic Classification

**Challenge:** Need consistent, testable logic

**Solution:** Rule-based keyword matching

```python
if "down" in description or "outage" in description:
    severity = "critical"
    incident_type = "service_outage"
```

**Code:** handlers.py:38-71

### 5. Batch Processing

**Solution:** Progress tracking with error handling

```python
for i, incident in enumerate(incidents):
    try:
        result = agent.triage_incident(incident)
        print(f"✓ Incident {i} completed")
    except Exception as e:
        print(f"✗ Error: {e}")
```

**Code:** cli_agent.py:179-206

## Code Organization

**agent/core.py:** Main agent loop, validation
**agent/llm_client.py:** Multi-provider integration
**functions/handlers.py:** Function implementations
**agent/cli_agent.py:** CLI interface
**ui/app.py:** Streamlit web UI

## Critical Patterns

### Pattern 1: Function Execution Loop

```python
while iteration < max_iterations:
    response, calls = llm_client.call_with_functions(messages, functions)
    if response:
        return response
    
    result = execute_function(calls[-1]["function"], calls[-1]["arguments"])
    messages.append({"role": "tool", "content": json.dumps(result)})
```

### Pattern 2: Validation

```python
def validate_result(result):
    if not result.get("incident_details"):
        return {"valid": False, "issues": ["Missing incident_details"]}
    return {"valid": True}
```

### Pattern 3: HTTP Helper

```python
def _http_post(url, headers, payload):
    if _HAS_REQUESTS:
        return requests.post(url, headers=headers, json=payload).json()
    else:
        # urllib fallback
```

## Challenges & Solutions

1. **Groq model deprecation** → Updated to llama-3.3-70b-versatile
2. **Gemini rate limiting** → Multi-provider cascade
3. **Format inconsistencies** → Translation layer
4. **Conversation corruption** → Explicit message tracking

## Dependencies

```
python-dotenv==1.0.0
requests>=2.31.0 (optional)
streamlit>=1.31.0 (optional)
```

## Lessons Learned

1. Test with actual APIs early
2. Multi-provider essential for reliability
3. Logging critical for debugging
4. Validation catches silent failures
5. Deterministic functions = predictable agents
