class MetricsTracker:
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.response_times = []     # Server-side processing time (x-process-time)
        self.inference_times = []    # Store ML/GPU inference times
        self.detailed_requests = []  # Store detailed timing for each request
        self.status_codes = {}
        self.errors = {}
        self.failed_traces = []      # Store trace IDs for failed requests
        self.slow_traces = []        # Store trace IDs for slow requests (>5s)
        self.successful_traces = []  # Store trace IDs for successful requests (up to 200)
        self.start_time = None
        self.end_time = None

    def record_request(self, status_code, response_time, error=None, trace_id=None, inference_time=0):
        try:
            self.total_requests += 1
            self.response_times.append(response_time)

            if inference_time > 0:
                self.inference_times.append(inference_time)

            # Store detailed timing for this request
            # response_time = x-process-time (server-side total)
            # inference_time = X-Inference-Model-Time (ML/GPU only)
            # non_inference_time = API overhead (server_time - inference_time)
            non_inference_time = response_time - inference_time if inference_time > 0 else response_time

            self.detailed_requests.append({
                "request_num": self.total_requests,
                "status_code": status_code,
                "server_time": response_time,             # x-process-time (server-side total)
                "inference_time": inference_time,         # ML/GPU time
                "non_inference_time": non_inference_time, # API overhead
                "trace_id": trace_id
            })

            self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1

            if status_code == 200:
                self.successful_requests += 1
                # Store trace ID for successful requests (limit to 200 to prevent memory bloat)
                if trace_id and len(self.successful_traces) < 200:
                    self.successful_traces.append({
                        "trace_id": trace_id,
                        "status_code": status_code,
                        "response_time": response_time
                    })
            else:
                self.failed_requests += 1
                # Store trace ID for failed requests
                if trace_id:
                    self.failed_traces.append({
                        "trace_id": trace_id,
                        "status_code": status_code,
                        "response_time": response_time,
                        "error": str(error) if error else None
                    })

            # Store trace ID for slow requests (regardless of success)
            if response_time > 5.0 and trace_id:
                self.slow_traces.append({
                    "trace_id": trace_id,
                    "status_code": status_code,
                    "response_time": response_time
                })

            if error:
                self.errors[str(error)] = self.errors.get(str(error), 0) + 1
        except Exception as e:
            from loguru import logger
            logger.error(f"Error recording metrics: {e}")
    
    def get_summary(self):
        try:
            if not self.response_times:
                return {
                    "total_requests": 0,
                    "successful": 0,
                    "failed": 0,
                    "success_rate": "0%",
                    "duration_seconds": "0.00",
                    "requests_per_second": "0",
                    "response_times": {
                        "min": "N/A",
                        "max": "N/A",
                        "avg": "N/A",
                        "median": "N/A",
                        "p95": "N/A",
                        "p99": "N/A"
                    },
                    "status_codes": {},
                    "top_errors": {},
                    "failed_traces": [],
                    "slow_traces": [],
                    "successful_traces": []
                }

            sorted_times = sorted(self.response_times)
            n = len(sorted_times)

            duration = (self.end_time - self.start_time) if (self.end_time and self.start_time) else 0

            # Calculate inference time statistics if available
            inference_stats = {}
            if self.inference_times:
                sorted_inf = sorted(self.inference_times)
                n_inf = len(sorted_inf)
                avg_response = sum(sorted_times) / n if n > 0 else 0
                avg_inference = sum(sorted_inf) / n_inf if n_inf > 0 else 0
                avg_non_inference = avg_response - avg_inference if avg_inference > 0 else 0

                inference_stats = {
                    "avg_inference_time": f"{avg_inference:.3f}s",
                    "avg_non_inference_time": f"{avg_non_inference:.3f}s",
                    "inference_percentage": f"{(avg_inference/avg_response*100):.1f}%" if avg_response > 0 else "0%",
                    "non_inference_percentage": f"{(avg_non_inference/avg_response*100):.1f}%" if avg_response > 0 else "0%"
                }

            return {
                "total_requests": self.total_requests,
                "successful": self.successful_requests,
                "failed": self.failed_requests,
                "success_rate": f"{(self.successful_requests/self.total_requests*100):.2f}%" if self.total_requests > 0 else "0%",
                "duration_seconds": f"{duration:.2f}",
                "requests_per_second": f"{self.total_requests/duration:.2f}" if duration > 0 else "0",
                "response_times": {
                    "min": f"{min(sorted_times):.2f}s",
                    "max": f"{max(sorted_times):.2f}s",
                    "avg": f"{sum(sorted_times)/n:.2f}s",
                    "median": f"{sorted_times[n//2]:.2f}s",
                    "p95": f"{sorted_times[int(n*0.95)]:.2f}s" if n > 20 else "N/A",
                    "p99": f"{sorted_times[int(n*0.99)]:.2f}s" if n > 100 else "N/A",
                },
                "status_codes": self.status_codes,
                "top_errors": dict(list(sorted(self.errors.items(), key=lambda x: x[1], reverse=True))[:5]) if self.errors else {},
                "failed_traces": self.failed_traces[:20],  # Include up to 20 failed trace IDs
                "slow_traces": sorted(self.slow_traces, key=lambda x: x["response_time"], reverse=True)[:20],  # Top 20 slowest
                "successful_traces": self.successful_traces,  # All successful traces (up to 200)
                "detailed_requests": self.detailed_requests,  # Detailed timing for each request
                **inference_stats  # Include inference timing breakdown if available
            }
        except Exception as e:
            from loguru import logger
            logger.error(f"Error generating summary: {e}")
            return {"error": str(e)}

    def print_detailed_table(self):
        """Print a formatted table of detailed request timings"""
        if not self.detailed_requests:
            print("No detailed request data available")
            return

        print("\n" + "="*80)
        print("DETAILED REQUEST TIMINGS (Server-Side Only)")
        print("="*80)
        print(f"{'Req#':<6} {'Status':<8} {'Server Time':<12} {'Inference':<12} {'Non-Inference':<15} {'Inf %':<8}")
        print("-"*80)

        for req in self.detailed_requests:
            server_time = req['server_time']
            inf = req['inference_time']
            non_inf = req['non_inference_time']
            inf_pct = (inf / server_time * 100) if server_time > 0 and inf > 0 else 0

            print(f"{req['request_num']:<6} "
                  f"{req['status_code']:<8} "
                  f"{server_time:<12.3f} "
                  f"{inf:<12.3f} "
                  f"{non_inf:<15.3f} "
                  f"{inf_pct:<8.1f}")

        print("="*80)

# Global metrics instance
metrics = MetricsTracker()