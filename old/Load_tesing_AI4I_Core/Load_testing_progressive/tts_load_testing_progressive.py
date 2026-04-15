"""
TTS Progressive Load Testing with Enhanced Metrics - AI4I Core API

This script gradually increases load and captures detailed per-stage metrics.

Usage:
    locust -f Load_tesing_AI4I_Core/Load_testing_progressive/tts_load_testing_progressive.py

Output:
    - Real-time stage transitions in console
    - Per-stage metrics in JSON output
    - Error rate, latency, and payload analysis for each stage
"""

from locust import LoadTestShape, events
from locust.runners import WorkerRunner
import time
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any

# Import from local config_progressive module
from config_progressive import TTSUser, TTSConfig

# Global tracking for per-stage metrics
stage_metrics: Dict[str, Dict] = {}
current_stage_name = None
stage_start_time = None
stage_requests_snapshot = 0
stage_failures_snapshot = 0


class ProgressiveLoadShape(LoadTestShape):
    """
    Progressive load shape with per-stage metrics tracking for AI4I Core API
    """

    stages = [
        # Stage 1: Warm-up - Gentle start
        {"duration": 120, "users": 5, "spawn_rate": 1, "name": "Stage 1: Warm-up (5 users)"},

        # Stage 2: Baseline - Establish stable performance
        {"duration": 240, "users": 10, "spawn_rate": 1, "name": "Stage 2: Baseline (10 users)"},

        # Stage 3: Light stress - Gradual increase
        {"duration": 360, "users": 15, "spawn_rate": 1, "name": "Stage 3: Light Stress (15 users)"}

        # # Stage 4: Medium load - Hold and observe
        # {"duration": 480, "users": 20, "spawn_rate": 1, "name": "Stage 4: Medium Load (20 users)"},

        # # Stage 5: Heavy stress - Push harder
        # {"duration": 600, "users": 30, "spawn_rate": 2, "name": "Stage 5: Heavy Stress (30 users)"},

        # # Stage 6: Peak load - Hold at high load
        # {"duration": 720, "users": 40, "spawn_rate": 2, "name": "Stage 6: Peak Load (40 users)"},

        # # Stage 7: Cool down - Scale back down
        # {"duration": 780, "users": 10, "spawn_rate": 3, "name": "Stage 7: Cool Down (10 users)"},
    ]

    def tick(self):
        """Returns (user_count, spawn_rate) and tracks stage transitions"""
        global current_stage_name, stage_start_time, stage_requests_snapshot, stage_failures_snapshot

        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                # Detect stage transition
                if current_stage_name != stage["name"]:
                    # Save previous stage metrics
                    if current_stage_name is not None:
                        capture_stage_metrics(self, current_stage_name, stage_start_time)

                    # Start new stage
                    current_stage_name = stage["name"]
                    stage_start_time = time.time()

                    # Snapshot current totals
                    if hasattr(self, 'runner') and self.runner:
                        stats = self.runner.stats.total
                        stage_requests_snapshot = stats.num_requests
                        stage_failures_snapshot = stats.num_failures
                        print(f"[DEBUG] New snapshot taken: {stage_requests_snapshot} requests")
                    else:
                        print(f"[WARNING] Could not take snapshot - runner not available")

                    print(f"\n{'='*70}")
                    print(f"🔄 {stage['name']}")
                    print(f"Time: {run_time:.0f}s | Target Users: {stage['users']} | Spawn Rate: {stage['spawn_rate']}/s")
                    print(f"{'='*70}\n")

                return (stage["users"], stage["spawn_rate"])

        # Test complete - save final stage
        if current_stage_name is not None:
            capture_stage_metrics(self, current_stage_name, stage_start_time)

        # Auto-quit after all stages complete
        print(f"\n{'='*70}")
        print("✅ All stages completed - stopping test automatically...")
        print(f"{'='*70}\n")

        # Stop the test gracefully
        if hasattr(self, 'runner') and self.runner:
            self.runner.quit()

        return None


def capture_stage_metrics(shape_instance, stage_name: str, start_time: float):
    """Capture metrics for the completed stage"""
    global stage_metrics, stage_requests_snapshot, stage_failures_snapshot

    if not hasattr(shape_instance, 'runner') or not shape_instance.runner:
        return

    stats = shape_instance.runner.stats.total
    end_time = time.time()
    duration = end_time - start_time

    # Calculate stage-specific metrics
    stage_requests = stats.num_requests - stage_requests_snapshot
    stage_failures = stats.num_failures - stage_failures_snapshot

    # Debug logging to track snapshot values
    print(f"[DEBUG] Stage: {stage_name}")
    print(f"[DEBUG] Current total requests: {stats.num_requests}")
    print(f"[DEBUG] Snapshot at stage start: {stage_requests_snapshot}")
    print(f"[DEBUG] Stage requests calculated: {stage_requests}")

    stage_success_rate = ((stage_requests - stage_failures) / stage_requests * 100) if stage_requests > 0 else 0
    stage_error_rate = (stage_failures / stage_requests * 100) if stage_requests > 0 else 0

    # Get current response time stats
    metrics = {
        "duration_seconds": round(duration, 2),
        "start_time": datetime.fromtimestamp(start_time).isoformat(),
        "end_time": datetime.fromtimestamp(end_time).isoformat(),
        "requests": {
            "total": stage_requests,
            "successful": stage_requests - stage_failures,
            "failed": stage_failures,
            "success_rate_percentage": round(stage_success_rate, 2),
            "error_rate_percentage": round(stage_error_rate, 2)
        },
        "latency_ms": {
            "min": round(stats.min_response_time, 2),
            "max": round(stats.max_response_time, 2),
            "median": round(stats.median_response_time, 2),
            "average": round(stats.avg_response_time, 2),
            "p95": round(stats.get_response_time_percentile(0.95), 2),
            "p99": round(stats.get_response_time_percentile(0.99), 2)
        },
        "throughput": {
            "requests_per_second": round(stage_requests / duration, 2) if duration > 0 else 0,
            "average_content_size_bytes": round(stats.avg_content_length, 2),
            "median_content_size_bytes": round(stats.median_content_length, 2) if hasattr(stats, 'median_content_length') else round(stats.avg_content_length, 2)
        }
    }

    stage_metrics[stage_name] = metrics

    # Print stage summary
    print(f"\n{'─'*70}")
    print(f"📊 {stage_name} - COMPLETED")
    print(f"Duration: {duration:.0f}s | Requests: {stage_requests} | Failures: {stage_failures}")
    print(f"Success Rate: {stage_success_rate:.2f}% | Error Rate: {stage_error_rate:.2f}%")
    print(f"Latency - Avg: {stats.avg_response_time:.0f}ms | P95: {stats.get_response_time_percentile(0.95):.0f}ms | P99: {stats.get_response_time_percentile(0.99):.0f}ms")
    print(f"Throughput: {stage_requests / duration:.2f} req/s")
    print(f"{'─'*70}\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Save detailed per-stage results to JSON"""
    global stage_metrics

    # Only save on master (not on workers in distributed mode)
    if isinstance(environment.runner, WorkerRunner):
        return

    print("\n" + "="*70)
    print("📊 TTS PROGRESSIVE LOAD TEST COMPLETED - AI4I Core API")
    print("="*70)

    stats = environment.stats.total

    # Validate stage metrics against overall total
    total_stage_requests = sum(stage.get("requests", {}).get("total", 0) for stage in stage_metrics.values())
    print(f"\n🔍 VALIDATION:")
    print(f"Total requests from Locust stats: {stats.num_requests}")
    print(f"Total requests from stage metrics: {total_stage_requests}")
    if total_stage_requests != stats.num_requests:
        discrepancy = abs(total_stage_requests - stats.num_requests)
        print(f"⚠️  WARNING: Discrepancy detected: {discrepancy} requests difference")
        print(f"⚠️  Stage metrics may be inaccurate due to snapshot timing issues")

    # Overall test summary
    print(f"\n🔍 OVERALL TEST SUMMARY:")
    print(f"Total Duration: {environment.runner.state}")
    print(f"Total Requests: {stats.num_requests}")
    print(f"Total Failures: {stats.num_failures}")
    if stats.num_requests > 0:
        print(f"Overall Success Rate: {((stats.num_requests - stats.num_failures) / stats.num_requests * 100):.2f}%")
        print(f"Overall Error Rate: {(stats.num_failures / stats.num_requests * 100):.2f}%")

    # Analyze breaking point
    print(f"\n🎯 CAPACITY ANALYSIS:")
    breaking_point = analyze_breaking_point(stage_metrics)
    if breaking_point:
        print(f"Breaking Point: {breaking_point['stage']}")
        print(f"Max Healthy Load: ~{breaking_point['max_users']} concurrent users")
        print(f"Recommendation: Run production with max {breaking_point['recommended_users']} users")

    # Build comprehensive JSON output
    output = build_enhanced_json_output(environment, stage_metrics)

    # Add validation metadata to the output
    output["validation"] = {
        "locust_total_requests": stats.num_requests,
        "stage_total_requests": total_stage_requests,
        "discrepancy": total_stage_requests - stats.num_requests,
        "note": "Use 'locust_total_requests' as the source of truth. Stage metrics may have snapshot timing issues."
    }

    # Save to file
    save_enhanced_results(output)

    print("="*70 + "\n")


def analyze_breaking_point(metrics: Dict) -> Dict[str, Any]:
    """Analyze metrics to find the breaking point"""
    breaking_point = None
    max_healthy_users = 0

    for stage_name, stage_data in metrics.items():
        error_rate = stage_data["requests"]["error_rate_percentage"]
        avg_latency = stage_data["latency_ms"]["average"]

        # Extract user count from stage name
        if "(" in stage_name and "users)" in stage_name:
            users_str = stage_name.split("(")[1].split(" users")[0]
            try:
                users = int(users_str)
            except:
                continue

            # Define healthy thresholds
            is_healthy = error_rate < 5 and avg_latency < 5000  # <5% errors, <5s latency

            if is_healthy:
                max_healthy_users = max(max_healthy_users, users)
            elif breaking_point is None and not is_healthy:
                breaking_point = {
                    "stage": stage_name,
                    "users": users,
                    "max_users": max_healthy_users,
                    "recommended_users": int(max_healthy_users * 0.8),  # 80% of max for safety
                    "error_rate": error_rate,
                    "avg_latency_ms": avg_latency
                }

    return breaking_point


def build_enhanced_json_output(environment, stage_metrics: Dict) -> Dict[str, Any]:
    """Build comprehensive JSON output with per-stage metrics"""
    stats = environment.stats.total

    # Get test configuration
    from dotenv import load_dotenv
    load_dotenv(override=True)
    config = TTSConfig()

    # Overall statistics
    overall_stats = {
        "test_info": {
            "test_type": "progressive_load_testing",
            "service": "TTS (Text-to-Speech) - AI4I Core API",
            "api_endpoint": "/api/v1/tts/inference",
            "test_date": datetime.now().isoformat(),
            "total_duration_seconds": time.time() - environment.stats.start_time,
        },
        "test_config": {
            "base_url": config.base_url,
            "service_id": config.service_id,
            "source_language": config.source_language,
            "gender": config.gender,
            "sampling_rate": config.sampling_rate,
            "audio_format": config.audio_format,
            "control_config": config.control_config
        },
        "overall_statistics": {
            "total_requests": stats.num_requests,
            "failed_requests": stats.num_failures,
            "successful_requests": stats.num_requests - stats.num_failures,
            "success_rate_percentage": round(((stats.num_requests - stats.num_failures) / stats.num_requests * 100), 2) if stats.num_requests > 0 else 0,
            "error_rate_percentage": round((stats.num_failures / stats.num_requests * 100), 2) if stats.num_requests > 0 else 0,
            "overall_latency_ms": {
                "min": round(stats.min_response_time, 2),
                "max": round(stats.max_response_time, 2),
                "median": round(stats.median_response_time, 2),
                "average": round(stats.avg_response_time, 2),
                "p95": round(stats.get_response_time_percentile(0.95), 2),
                "p99": round(stats.get_response_time_percentile(0.99), 2)
            },
            "overall_throughput": {
                "total_rps": round(stats.total_rps, 2),
                "average_content_size_bytes": round(stats.avg_content_length, 2),
                "median_content_size_bytes": round(stats.median_content_length, 2) if hasattr(stats, 'median_content_length') else round(stats.avg_content_length, 2)
            }
        },
        "stage_by_stage_metrics": stage_metrics,
        "capacity_analysis": analyze_capacity(stage_metrics),
        "recommendations": generate_recommendations(stage_metrics)
    }

    return overall_stats


def analyze_capacity(stage_metrics: Dict) -> Dict[str, Any]:
    """Detailed capacity analysis"""
    analysis = {
        "healthy_stages": [],
        "degraded_stages": [],
        "failed_stages": [],
        "breaking_point": None,
        "max_healthy_capacity": None
    }

    for stage_name, metrics in stage_metrics.items():
        error_rate = metrics["requests"]["error_rate_percentage"]
        avg_latency = metrics["latency_ms"]["average"]
        p95_latency = metrics["latency_ms"]["p95"]

        stage_summary = {
            "stage": stage_name,
            "error_rate": error_rate,
            "avg_latency_ms": avg_latency,
            "p95_latency_ms": p95_latency
        }

        # Classify stage health
        if error_rate < 1 and p95_latency < 5000:
            analysis["healthy_stages"].append(stage_summary)
            # Extract user count
            if "(" in stage_name and "users)" in stage_name:
                users_str = stage_name.split("(")[1].split(" users")[0]
                try:
                    users = int(users_str)
                    if analysis["max_healthy_capacity"] is None or users > analysis["max_healthy_capacity"]:
                        analysis["max_healthy_capacity"] = users
                except:
                    pass
        elif error_rate < 10 and p95_latency < 15000:
            analysis["degraded_stages"].append(stage_summary)
            if analysis["breaking_point"] is None:
                analysis["breaking_point"] = stage_name
        else:
            analysis["failed_stages"].append(stage_summary)
            if analysis["breaking_point"] is None:
                analysis["breaking_point"] = stage_name

    return analysis


def generate_recommendations(stage_metrics: Dict) -> Dict[str, Any]:
    """Generate actionable recommendations"""
    capacity_analysis = analyze_capacity(stage_metrics)

    recommendations = {
        "production_capacity": None,
        "scaling_needed": False,
        "optimization_priority": [],
        "action_items": []
    }

    max_healthy = capacity_analysis["max_healthy_capacity"]

    if max_healthy:
        recommended_capacity = int(max_healthy * 0.7)  # 70% of max for safety margin
        recommendations["production_capacity"] = f"{recommended_capacity} concurrent users (70% of max tested: {max_healthy})"
        recommendations["action_items"].append(f"Set production max concurrent users to {recommended_capacity}")
    else:
        recommendations["production_capacity"] = "Server cannot handle load - immediate attention required"
        recommendations["scaling_needed"] = True
        recommendations["action_items"].append("URGENT: Server fails under minimal load - investigate immediately")

    # Analyze failure patterns
    if capacity_analysis["failed_stages"]:
        recommendations["optimization_priority"].append("High error rates detected - investigate server logs")

    # Check latency issues
    for stage_name, metrics in stage_metrics.items():
        if metrics["latency_ms"]["p99"] > 30000:  # P99 > 30s
            recommendations["optimization_priority"].append(f"High P99 latency in {stage_name} - optimize response time")
            break

    if not recommendations["optimization_priority"]:
        recommendations["optimization_priority"].append("System performing well within tested range")

    return recommendations


def save_enhanced_results(output: Dict[str, Any]):
    """Save enhanced results to JSON file"""
    # Determine save path - go to Load_testing_progressive_results folder
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)  # Load_tesing_AI4I_Core
    results_dir = os.path.join(parent_dir, "Load_testing_progressive_results")
    os.makedirs(results_dir, exist_ok=True)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(results_dir, f"tts_progressive_results_{timestamp}.json")

    # Save JSON
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Detailed results saved to: {filename}")
    print(f"\n📊 Key Findings:")

    capacity = output.get("capacity_analysis", {})
    if capacity.get("max_healthy_capacity"):
        print(f"   Max Healthy Capacity: {capacity['max_healthy_capacity']} concurrent users")

    if capacity.get("breaking_point"):
        print(f"   Breaking Point: {capacity['breaking_point']}")

    recommendations = output.get("recommendations", {})
    if recommendations.get("production_capacity"):
        print(f"   Recommended Production Capacity: {recommendations['production_capacity']}")


class ConservativeProgressiveLoad(LoadTestShape):
    """
    Very conservative progressive load - for severely struggling servers.
    Increases load very slowly to find exact breaking point.

    Total duration: ~15 minutes
    """

    stages = [
        {"duration": 60, "users": 2, "spawn_rate": 1, "name": "Stage 1: 2 users"},
        {"duration": 180, "users": 2, "spawn_rate": 1, "name": "Stage 1 Hold"},

        {"duration": 240, "users": 5, "spawn_rate": 1, "name": "Stage 2: 5 users"},
        {"duration": 360, "users": 5, "spawn_rate": 1, "name": "Stage 2 Hold"},

        {"duration": 420, "users": 8, "spawn_rate": 1, "name": "Stage 3: 8 users"},
        {"duration": 540, "users": 8, "spawn_rate": 1, "name": "Stage 3 Hold"},

        {"duration": 600, "users": 12, "spawn_rate": 1, "name": "Stage 4: 12 users"},
        {"duration": 720, "users": 12, "spawn_rate": 1, "name": "Stage 4 Hold"},

        {"duration": 780, "users": 15, "spawn_rate": 1, "name": "Stage 5: 15 users"},
        {"duration": 900, "users": 15, "spawn_rate": 1, "name": "Stage 5 Hold"},
    ]

    def tick(self):
        global current_stage_name, stage_start_time, stage_requests_snapshot, stage_failures_snapshot

        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                if current_stage_name != stage["name"]:
                    if current_stage_name is not None:
                        capture_stage_metrics(self, current_stage_name, stage_start_time)

                    current_stage_name = stage["name"]
                    stage_start_time = time.time()

                    if hasattr(self, 'runner') and self.runner:
                        stats = self.runner.stats.total
                        stage_requests_snapshot = stats.num_requests
                        stage_failures_snapshot = stats.num_failures

                    print(f"\n{'='*70}")
                    print(f"STAGE: {stage['name']}")
                    print(f"Time: {run_time:.0f}s | Target Users: {stage['users']} | Spawn Rate: {stage['spawn_rate']}/s")
                    print(f"{'='*70}\n")

                return (stage["users"], stage["spawn_rate"])

        if current_stage_name is not None:
            capture_stage_metrics(self, current_stage_name, stage_start_time)

        print(f"\n{'='*70}")
        print("✅ All stages completed - stopping test automatically...")
        print(f"{'='*70}\n")

        if hasattr(self, 'runner') and self.runner:
            self.runner.quit()

        return None


class AggressiveProgressiveLoad(LoadTestShape):
    """
    Aggressive progressive load - for finding limits quickly.
    Rapidly increases load to find breaking point fast.

    Total duration: ~10 minutes
    """

    stages = [
        {"duration": 60, "users": 10, "spawn_rate": 2, "name": "Quick Start (10 users)"},
        {"duration": 150, "users": 10, "spawn_rate": 2, "name": "Quick Start Hold"},

        {"duration": 210, "users": 25, "spawn_rate": 3, "name": "Rapid Ramp (25 users)"},
        {"duration": 300, "users": 25, "spawn_rate": 3, "name": "Rapid Hold"},

        {"duration": 360, "users": 50, "spawn_rate": 5, "name": "Heavy Push (50 users)"},
        {"duration": 450, "users": 50, "spawn_rate": 5, "name": "Heavy Hold"},

        {"duration": 510, "users": 75, "spawn_rate": 5, "name": "Breaking Point (75 users)"},
        {"duration": 600, "users": 75, "spawn_rate": 5, "name": "Observation"},
    ]

    def tick(self):
        global current_stage_name, stage_start_time, stage_requests_snapshot, stage_failures_snapshot

        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                if current_stage_name != stage["name"]:
                    if current_stage_name is not None:
                        capture_stage_metrics(self, current_stage_name, stage_start_time)

                    current_stage_name = stage["name"]
                    stage_start_time = time.time()

                    if hasattr(self, 'runner') and self.runner:
                        stats = self.runner.stats.total
                        stage_requests_snapshot = stats.num_requests
                        stage_failures_snapshot = stats.num_failures

                    print(f"\n{'='*70}")
                    print(f"STAGE: {stage['name']}")
                    print(f"Time: {run_time:.0f}s | Target Users: {stage['users']}")
                    print(f"{'='*70}\n")

                return (stage["users"], stage["spawn_rate"])

        if current_stage_name is not None:
            capture_stage_metrics(self, current_stage_name, stage_start_time)

        print(f"\n{'='*70}")
        print("✅ All stages completed - stopping test automatically...")
        print(f"{'='*70}\n")

        if hasattr(self, 'runner') and self.runner:
            self.runner.quit()

        return None


# Default load shape - comment/uncomment to switch between shapes
# Use ProgressiveLoadShape for normal capacity testing (recommended, ~13 min)
class CustomLoadShape(ProgressiveLoadShape):
    pass

# Or use ConservativeProgressiveLoad if server is very weak (~15 min)
# class CustomLoadShape(ConservativeProgressiveLoad):
#     pass

# Or use AggressiveProgressiveLoad to find limits quickly (~10 min)
# class CustomLoadShape(AggressiveProgressiveLoad):
#     pass


if __name__ == "__main__":
    print("\n" + "="*70)
    print("TTS Progressive Load Testing with Enhanced Metrics - AI4I Core API")
    print("="*70)
    print("\nThis script captures detailed per-stage metrics:")
    print("  ✓ Error rate per stage")
    print("  ✓ Latency (min, max, median, avg, P95, P99) per stage")
    print("  ✓ Payload size per stage")
    print("  ✓ Throughput per stage")
    print("  ✓ Capacity analysis")
    print("  ✓ Breaking point detection")
    print("  ✓ Production recommendations")
    print("\nTo run this test:")
    print("  locust -f Load_tesing_AI4I_Core/Load_testing_progressive/tts_load_testing_progressive.py")
    print("\nResults will be saved to:")
    print("  Load_tesing_AI4I_Core/Load_testing_progressive_results/tts_progressive_results_TIMESTAMP.json")
    print("="*70 + "\n")
