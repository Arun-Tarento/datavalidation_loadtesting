# Implementing Jaeger/OpenTelemetry for NMT Timing Analysis

## Overview

Jaeger + OpenTelemetry would give you **complete visibility** into request timing without any client-side instrumentation. This is the enterprise-grade solution used by companies like Uber, Netflix, and Microsoft.

---

## ✅ What You'd Get

### Before (Current State):
```
Client sees: Total time = 2.5s
❓ What happened in those 2.5s? Unknown.
```

### After (With Jaeger):
```
Jaeger Trace View:
┌─────────────────────────────────────────────────────────┐
│ HTTP Request                           [2.45s]          │
│  ├─ Token Validation                   [0.025s]         │
│  ├─ Rate Limit Check                   [0.008s]         │
│  ├─ Input Validation                   [0.012s]         │
│  ├─ Preprocessing                      [0.045s]         │
│  ├─ ML Inference (NMT Model)           [1.85s]  ← Tag to exclude │
│  ├─ Postprocessing                     [0.032s]         │
│  └─ Response Serialization             [0.018s]         │
└─────────────────────────────────────────────────────────┘
Total: 2.45s | Non-inference: 0.60s | Inference: 1.85s
```

**You can then:**
- Filter traces by `span.name != "ml.inference"`
- Export non-inference metrics to Prometheus
- Create dashboards showing bottlenecks
- Alert when non-inference time exceeds threshold

---

## 🏗️ Architecture

### Server-Side (Backend Changes Required)

```python
# Example: FastAPI + OpenTelemetry instrumentation
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Setup (one-time, in main.py)
trace.set_tracer_provider(TracerProvider())
jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)

# Auto-instrument FastAPI
app = FastAPI()
FastAPIInstrumentor.instrument_app(app)

# Manual instrumentation for ML inference
tracer = trace.get_tracer(__name__)

@app.post("/api/v1/nmt/inference")
async def nmt_inference(request: NMTRequest):
    # Auth, validation happen automatically (traced by FastAPI instrumentation)

    # Manually trace the inference step
    with tracer.start_as_current_span("ml.inference") as span:
        span.set_attribute("model.name", "nmt-hi-en")
        span.set_attribute("input.length", len(request.input))

        result = await model.translate(request.input)  # The actual ML call

        span.set_attribute("inference.duration_ms", span.elapsed_time_ms)

    # Postprocessing happens here (auto-traced)
    return result
```

### Infrastructure

```yaml
# docker-compose.yml
version: '3'
services:
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # Jaeger UI
      - "6831:6831/udp"  # Agent port
    environment:
      - COLLECTOR_ZIPKIN_HTTP_PORT=9411

  ai4i-api:
    build: .
    environment:
      - JAEGER_AGENT_HOST=jaeger
      - JAEGER_AGENT_PORT=6831
    depends_on:
      - jaeger
```

---

## 📊 Client-Side (Your Load Tests)

**The beauty: Your load tests don't need to change!**

But you CAN enhance them to correlate with Jaeger traces:

```python
# In nmt_loadtesting.py
import uuid

@task
def nmt_task(self):
    # Generate trace ID to correlate with Jaeger
    trace_id = uuid.uuid4().hex

    headers = {
        "Authorization": f"Bearer {self.access_token}",
        "X-Trace-Id": trace_id,  # Pass to server
    }

    response = self.client.post(
        url=f"{base_url}/api/v1/nmt/inference",
        headers=headers,
        json=payload
    )

    # Log trace ID so you can look it up in Jaeger UI
    logger.info(f"Request trace: http://localhost:16686/trace/{trace_id}")
```

Then you can:
1. Run load test
2. Click the link in logs
3. See exact breakdown in Jaeger UI

---

## 🚀 Implementation Steps

### Phase 1: Basic Setup (1-2 days)

1. **Deploy Jaeger** (easiest with Docker)
   ```bash
   docker run -d -p 16686:16686 -p 6831:6831/udp jaegertracing/all-in-one:latest
   ```

2. **Add OpenTelemetry to API server**
   ```bash
   pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi opentelemetry-exporter-jaeger
   ```

3. **Auto-instrument the web framework** (FastAPI, Flask, Django, etc.)
   - This gives you basic request timing automatically
   - No code changes needed beyond initialization

4. **Verify in Jaeger UI**
   - Visit http://localhost:16686
   - Make a test request
   - See the trace appear

### Phase 2: Custom Spans (2-3 days)

5. **Add manual spans for ML inference**
   ```python
   with tracer.start_as_current_span("ml.inference"):
       result = model.predict(input)
   ```

6. **Add spans for other critical sections**
   - Database queries (may auto-instrument)
   - Redis cache lookups
   - External API calls

### Phase 3: Analysis & Dashboards (1-2 days)

7. **Export metrics to Prometheus**
   - OpenTelemetry can export metrics
   - Create Grafana dashboards

8. **Create alerts**
   - When non-inference time > threshold
   - When certain spans are slow

---

## 💰 Cost/Effort Analysis

| Approach | Setup Time | Maintenance | Granularity | Cost |
|----------|-----------|-------------|-------------|------|
| **Current (manual timing)** | Done | None | Low (total time only) | Free |
| **Response headers** | 1 day | Low | Medium (inference vs rest) | Free |
| **Jaeger/OpenTelemetry** | 3-7 days | Medium | **High (every layer)** | Free (self-hosted) |
| **Commercial APM** (DataDog, New Relic) | 1-2 days | Low | **High** | $$$ |

**Recommendation:**
- **If this is a one-time test**: Use response headers approach (quick win)
- **If this is ongoing monitoring**: Invest in Jaeger (industry standard)
- **If you have budget**: Commercial APM (easiest, best UX)

---

## 🎯 Minimal "Easy Fix" Version

If you want the **benefits of Jaeger without full commitment**:

### Option A: Just Add Response Headers (Easiest)

```python
# In your API server, after inference:
inference_time = time.time() - inference_start

response.headers["Server-Timing"] = f"inference;dur={inference_time*1000}"
# Or simpler:
response.headers["X-Inference-Time"] = str(inference_time)
```

**Then your load tests automatically see it** (use `visualize_timing.py` script I created earlier).

**Effort: 30 minutes** ✅

### Option B: OpenTelemetry Logging (No Jaeger UI)

Just add OpenTelemetry instrumentation but export to logs instead of Jaeger:

```python
# Export traces to stdout/logs
from opentelemetry.sdk.trace.export import ConsoleSpanExporter

trace.get_tracer_provider().add_span_processor(
    SimpleSpanProcessor(ConsoleSpanExporter())
)
```

**Then parse logs during load tests.**

**Effort: 2-3 hours** ✅

---

## 🔍 Example: What You'd See in Jaeger UI

After running your load test, visit Jaeger UI:

```
Service: ai4i-nmt-api
Operation: POST /api/v1/nmt/inference

Trace Timeline (2.45s total):
┌────────────────────────────────────────────────────────────┐
│ fastapi.request                                    [2.45s] │
│  │                                                          │
│  ├─ auth.validate_token                           [0.025s] │
│  │                                                          │
│  ├─ middleware.rate_limit                         [0.008s] │
│  │                                                          │
│  ├─ nmt.validate_input                            [0.012s] │
│  │                                                          │
│  ├─ nmt.preprocess                                [0.045s] │
│  │   ├─ text.normalize                            [0.020s] │
│  │   └─ text.tokenize                             [0.025s] │
│  │                                                          │
│  ├─ ml.inference ⭐                                [1.85s]  │ ← THE LAYER YOU WANT TO EXCLUDE
│  │   ├─ model.load_from_cache                     [0.005s] │
│  │   └─ model.predict                             [1.845s] │
│  │                                                          │
│  ├─ nmt.postprocess                               [0.032s] │
│  │   └─ text.detokenize                           [0.032s] │
│  │                                                          │
│  └─ response.serialize                            [0.018s] │
└────────────────────────────────────────────────────────────┘

🎯 Query in Jaeger:
   - Service: ai4i-nmt-api
   - Min Duration: 0s
   - Max Duration: 10s
   - Tags: span.kind=server AND span.name!="ml.inference"

   Shows only non-inference traces!
```

---

## 📝 Decision Matrix

| You Control Backend? | Recommended Solution | Effort |
|---------------------|---------------------|--------|
| ✅ Yes, you own the API | **Jaeger + OpenTelemetry** | Medium (worth it) |
| ✅ Yes, need quick fix | **Response headers** | Low (30 min) |
| ❌ No, external API | **Request API team for headers** | Zero (your side) |
| ❌ No, they won't add headers | **Client-side TTFB only** | Already done ✅ |

---

## 🚦 Next Steps

1. **First, answer this question:** Do you control the `staging.ai4inclusion.org` backend?

   - **YES** → Proceed with Jaeger implementation
   - **NO** → Request API team to add `X-Inference-Time` header

2. **Quick win (30 min):** Add response header to API
   ```python
   response.headers["X-Inference-Time"] = str(inference_duration)
   ```

3. **Long-term (1 week):** Implement full Jaeger tracing

4. **Use existing tools:** The `visualize_timing.py` script I created will automatically detect and use any timing headers you add!

---

## 📚 Resources

- [OpenTelemetry Python Docs](https://opentelemetry.io/docs/instrumentation/python/)
- [Jaeger Getting Started](https://www.jaegertracing.io/docs/latest/getting-started/)
- [FastAPI + OpenTelemetry Tutorial](https://github.com/open-telemetry/opentelemetry-python-contrib/tree/main/instrumentation/opentelemetry-instrumentation-fastapi)
- [Server-Timing Header Spec](https://w3c.github.io/server-timing/)

---

## ❓ FAQ

**Q: Can I use Jaeger without modifying the backend?**
A: No, you need to instrument the server. But it's 90% automatic with OpenTelemetry.

**Q: What if I use Django/Flask instead of FastAPI?**
A: OpenTelemetry supports all major frameworks. Just swap `FastAPIInstrumentor` for `FlaskInstrumentor` or `DjangoInstrumentor`.

**Q: Can I export to Prometheus instead of Jaeger?**
A: Yes! OpenTelemetry can export to multiple backends simultaneously.

**Q: What's the performance overhead?**
A: Typically <1% CPU/memory with proper sampling (e.g., trace 10% of requests).

**Q: Can I filter specific users/requests in Jaeger?**
A: Yes, add custom attributes: `span.set_attribute("user.email", user_email)`
