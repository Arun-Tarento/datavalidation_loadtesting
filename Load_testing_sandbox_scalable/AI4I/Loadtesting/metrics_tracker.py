class MetricsTracker:
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.response_times = []
        self.status_codes = {}
        self.errors = {}
        self.start_time = None
        self.end_time = None
    
    def record_request(self, status_code, response_time, error=None):
        try:
            self.total_requests += 1
            self.response_times.append(response_time)
            
            self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
            
            if status_code == 200:
                self.successful_requests += 1
            else:
                self.failed_requests += 1
                
            if error:
                self.errors[str(error)] = self.errors.get(str(error), 0) + 1
        except Exception as e:
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
                    "top_errors": {}
                }
            
            sorted_times = sorted(self.response_times)
            n = len(sorted_times)
            
            duration = (self.end_time - self.start_time) if (self.end_time and self.start_time) else 0
            
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
                "top_errors": dict(list(sorted(self.errors.items(), key=lambda x: x[1], reverse=True))[:5]) if self.errors else {}
            }
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return {"error": str(e)}

# Global metrics instance
metrics = MetricsTracker()