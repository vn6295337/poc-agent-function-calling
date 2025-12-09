# Operations Guide

## Prerequisites

- Python 3.11+
- At least one LLM API key (Gemini, Groq, or OpenRouter)
- Virtual environment (recommended)

## Quick Start (5 minutes)

### 1. Setup

```bash
# Navigate to project
cd /home/vn6295337/poc-agent-function-calling

# Activate virtual environment
source ~/aienv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your keys
```

### 2. Run Single Incident

```bash
python agent/cli_agent.py --incident "Production database is down. Users cannot login. Connection timeout on port 5432."
```

### 3. Run Interactive Mode

```bash
python agent/cli_agent.py

# Enter incident description (multi-line supported)
# Type 'quit' to exit
```

### 4. Run Batch Processing

```bash
python agent/cli_agent.py --mode batch --batch-file tests/sample_incidents.json --output logs
```

### 5. Run Web UI

```bash
streamlit run ui/app.py
```

## Configuration

### Environment Variables

```bash
# LLM Provider API Keys (at least one required)
GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key  
OPENROUTER_API_KEY=your_openrouter_key

# Model Configuration (optional)
GEMINI_MODEL=gemini-2.0-flash-exp
GROQ_MODEL=llama-3.3-70b-versatile
OPENROUTER_MODEL=mistralai/mistral-7b-instruct:free
```

### Provider Priority

The system tries providers in this order:
1. Gemini (if key present)
2. Groq (if Gemini fails or no key)
3. OpenRouter (if Groq fails)

## Running Tests

### Test Single Incident

```bash
python agent/cli_agent.py --incident "Disk space at 95% on DB server" --save
# Result saved to: triage_result_TIMESTAMP.json
```

### Test Batch Processing

```bash
python agent/cli_agent.py --mode batch --batch-file tests/sample_incidents.json
# Results saved to: logs/batch_results.json
```

### View Test Results

```bash
# View saved result
cat triage_result_*.json | jq '.'

# View execution log
cat triage_result_*.json | jq '.execution_log'

# View validation
cat triage_result_*.json | jq '.validation'
```

## Monitoring

### Check Logs

```bash
# Real-time logs (INFO level)
python agent/cli_agent.py --incident "..." 2>&1 | grep INFO

# View execution metrics
cat triage_result_*.json | jq '{
  iterations: .total_iterations,
  function_calls: (.execution_log | length),
  successful_calls: [.execution_log[] | select(.status == "success")] | length
}'
```

### Performance Metrics

```bash
# Average response time
cat triage_result_*.json | jq '.execution_log[].timestamp' | wc -l

# Provider usage
cat triage_result_*.json | jq '.execution_log[].provider' | sort | uniq -c
```

## Troubleshooting

### Issue 1: "No LLM API key found"

**Symptom:** RuntimeError on startup

**Solution:**
```bash
# Check .env file exists
ls -la .env

# Verify at least one key is set
grep API_KEY .env

# Source environment
source .env
```

### Issue 2: "429 Too Many Requests"

**Symptom:** Rate limit errors

**Solution:**
- System automatically falls back to next provider
- If all providers exhausted, wait 1 minute or add another provider

### Issue 3: "Model decommissioned"

**Symptom:** 400 error mentioning model not supported

**Solution:**
```bash
# Update model in .env
GROQ_MODEL=llama-3.3-70b-versatile
```

### Issue 4: "Validation issues detected"

**Symptom:** Warning about missing fields

**Solution:**
- Non-blocking warning, partial results still returned
- Check execution_log for function failures
- May indicate LLM didn't call required functions

### Issue 5: Streamlit import error

**Symptom:** ModuleNotFoundError: streamlit

**Solution:**
```bash
pip install streamlit
```

## Common Operations

### Add Custom Incident Type

1. Edit `functions/schemas.json`:
```json
{
  "incident_type": {
    "enum": ["service_outage", "...", "your_new_type"]
  }
}
```

2. Edit `functions/handlers.py`:
```python
playbooks = {
    "your_new_type": {
        "immediate_actions": [...],
        "investigation_steps": [...],
        "escalation_criteria": "..."
    }
}
```

### Change Provider Priority

Edit `agent/llm_client.py`:
```python
# Change order in __init__
if self.groq_key:  # Try Groq first
    self.provider = "groq"
elif self.gemini_key:
    self.provider = "gemini"
```

### Export Results to CSV

```bash
cat logs/batch_results.json | jq -r '.[] | [.incident_number, .result.incident_details.severity, .result.incident_details.incident_type] | @csv' > results.csv
```

### View Function Call Trace

```bash
cat triage_result_*.json | jq '.execution_log[] | {
  function: .function,
  status: .status,
  timestamp: .timestamp
}'
```

## Production Deployment (Future)

### Recommended Setup

- **API Keys:** Use secrets manager (AWS Secrets Manager, HashiCorp Vault)
- **Persistence:** Add PostgreSQL for incident history
- **Monitoring:** Add Prometheus metrics export
- **Scaling:** Deploy behind load balancer with multiple instances

### Health Check Endpoint

Currently not implemented. For production, add:

```python
@app.route('/health')
def health():
    return {"status": "healthy", "provider": llm_client.provider}
```

## Backup & Recovery

### Backup Configuration

```bash
# Backup .env
cp .env .env.backup.$(date +%Y%m%d)

# Backup custom playbooks
cp functions/handlers.py functions/handlers.py.backup
```

### Restore Configuration

```bash
cp .env.backup.YYYYMMDD .env
```

## Performance Tuning

### Reduce Latency

- Use Groq (fastest, ~1-2s)
- Disable Gemini if rate limited
- Reduce max_iterations in core.py

### Increase Throughput

- Run multiple CLI instances in parallel
- Use batch mode instead of interactive
- Cache common incident patterns (future feature)

## Support

- **GitHub Issues:** https://github.com/vn6295337/poc-agent-function-calling/issues
- **Documentation:** See docs/ directory
- **Logs:** Check triage_result_*.json files
