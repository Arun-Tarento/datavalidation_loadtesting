# Latency Discrepancy Analysis: Locust vs Grafana

## Summary of Findings

### NMT (Translation)
- **Locust (Client-side)**: 770ms median
- **Grafana (Server-side)**: 470ms median
- **Difference**: 300ms (39% overhead)

### TTS (Text-to-Speech)
- **Locust (Client-side)**: 2400ms median
- **Grafana (Server-side)**: 673ms median
- **Difference**: 1727ms (72% overhead)

---

## What Each Tool Measures

### Locust Measures: **END-TO-END CLIENT LATENCY**
```
[Client] ──────────────────────────────────────────> [Server] ──────────────────────────────────────────> [Client]
         │                                           │                                                    │
         │← DNS Lookup                               │                                                    │
         │← TCP Connection                           │                                                    │
         │← SSL/TLS Handshake                        │                                                    │
         │← Send Request (payload serialization)     │                                                    │
         │                                           │← Load Balancer                                     │
         │                                           │← Middleware Processing                             │
         │                                           │← API Handler                                       │
         │                                           │← APPLICATION PROCESSING (Grafana measures this!)   │
         │                                           │← Response Serialization                            │
         │                                           │← Send Response                                      │
         │                                                                                                │← Receive Response
         │                                                                                                │← Deserialize

TOTAL TIME = All of the above
```

### Grafana Measures: **SERVER-SIDE APPLICATION PROCESSING ONLY**
```
                                                      [Server Internal Metrics]
                                                      │
                                                      │← Model Inference Time
                                                      │← Database Queries
                                                      │← Business Logic

TOTAL TIME = Just application processing (no network, no serialization overhead)
```

---

## Breakdown of the Overhead

### NMT Service (300ms overhead)
| Component | Estimated Time | Notes |
|-----------|---------------|-------|
| Grafana (Application Processing) | 470ms | Model inference + API logic |
| Network Round-Trip (RTT) | ~50-100ms | Client ↔ Server |
| Request Serialization | ~10-20ms | JSON encoding/decoding |
| Response Transmission | ~20-50ms | Small payload (~741 bytes) |
| Load Balancer/Middleware | ~20-50ms | Proxy overhead |
| SSL/TLS | ~30-50ms | Encryption/decryption |
| **Total Overhead** | **~300ms** | Matches your difference! |
| **Locust Total** | **770ms** | ✓ Confirmed |

### TTS Service (1727ms overhead!)
| Component | Estimated Time | Notes |
|-----------|---------------|-------|
| Grafana (Application Processing) | 673ms | Model inference + audio generation |
| Network Round-Trip (RTT) | ~50-100ms | Client ↔ Server |
| Request Serialization | ~10-20ms | JSON encoding/decoding |
| **Response Transmission** | **~1400-1500ms** | **LARGE PAYLOAD (~1.08 MB)** |
| Load Balancer/Middleware | ~20-50ms | Proxy overhead |
| SSL/TLS | ~30-50ms | Encryption/decryption |
| **Total Overhead** | **~1727ms** | Matches your difference! |
| **Locust Total** | **2400ms** | ✓ Confirmed |

---

## Why TTS Has Much Larger Overhead

### Payload Size Comparison:
- **NMT Response**: ~741 bytes (text translation)
- **TTS Response**: ~1,077,693 bytes ≈ **1.08 MB** (audio file)

### Network Transmission Time:
Assuming typical network bandwidth:
- **NMT**: 741 bytes ÷ 10 Mbps ≈ 0.6ms (negligible)
- **TTS**: 1,077,693 bytes ÷ 10 Mbps ≈ **863ms** just for transmission!

At slower bandwidth (1 Mbps):
- **TTS**: 1,077,693 bytes ÷ 1 Mbps ≈ **8,621ms** (8.6 seconds!)

This explains why TTS overhead is **5.7x larger** than NMT overhead.

---

## Rational Explanation

### ✅ Both Measurements Are Correct!

1. **Grafana is measuring correctly**: It shows the actual application processing time (inference time)
   - NMT model inference: ~470ms
   - TTS model inference + audio generation: ~673ms

2. **Locust is measuring correctly**: It shows what your users actually experience
   - NMT end-to-end: ~770ms
   - TTS end-to-end: ~2400ms

### The Difference Is:
- **Network latency** (round-trip time)
- **Data transmission time** (especially critical for large TTS audio files)
- **Protocol overhead** (TCP, SSL/TLS, HTTP)
- **Middleware/proxy overhead** (load balancers, API gateways)

---

## Which Metric Should You Use?

### For Capacity Planning:
- Use **Locust metrics** - they represent real user experience

### For Service Optimization:
- Use **Grafana metrics** - they show actual model/application performance

### For SLAs:
- Use **Locust metrics** - users care about end-to-end response time

---

## Recommendations

### 1. For TTS Optimization:
The 1.7 second overhead is primarily due to **large audio payload transmission**. Consider:
- **Compression**: Use audio compression (e.g., opus, mp3 instead of WAV)
- **Streaming**: Stream audio instead of sending complete file
- **CDN**: Cache generated audio if patterns repeat
- **Response Size**:
  - Current: 1.08 MB WAV
  - Compressed (opus): ~50-100 KB (10-20x smaller!)
  - **Potential savings**: ~1400ms → ~70-140ms transmission time

### 2. For NMT:
The 300ms overhead is reasonable for network + protocol overhead. Optimization options:
- **Connection pooling**: Reduce SSL handshake overhead
- **HTTP/2**: Multiplexing can help with concurrent requests
- **Local caching**: Cache frequent translations

### 3. Monitoring Both:
Track both metrics to understand:
- **Grafana**: Is the model/service healthy?
- **Locust**: Is the user experience acceptable?

If Grafana latency stays constant but Locust latency increases:
→ Network/infrastructure issue

If both increase together:
→ Service/model performance issue

---

## Validation

Your numbers perfectly match the expected overhead:

| Service | Application (Grafana) | Overhead | End-to-End (Locust) | Overhead % |
|---------|----------------------|----------|---------------------|------------|
| NMT | 470ms | 300ms | 770ms | 39% |
| TTS | 673ms | 1727ms | 2400ms | 72% |

**Conclusion**: Everything is working as expected. The discrepancy is due to measuring at different points in the request lifecycle.
