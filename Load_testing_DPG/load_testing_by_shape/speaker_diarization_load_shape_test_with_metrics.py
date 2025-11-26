"""
Speaker Diarization Load Shaping Test with Enhanced Metrics - Find Server Capacity

This script gradually increases load and captures detailed per-stage metrics.

Usage:
    locust -f Load_testing_DPG/load_testing_by_shape/speaker_diarization_load_shape_test_with_metrics.py --host=http://13.204.164.186:8000

Output:
    - Real-time stage transitions in console
    - Per-stage metrics in JSON output
    - Error rate, latency, and payload analysis for each stage
    - Error code distribution
    - Audio length analysis
"""

from locust import LoadTestShape, events
from locust.runners import WorkerRunner
import time
import json
import os
import sys
import base64
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict

# Import from local shape_config module
from shape_config import SpeakerDiarizationUser, SpeakerDiarizationConfig

# Global tracking for per-stage metrics
stage_metrics: Dict[str, Dict] = {}
current_stage_name = None
stage_start_time = None
stage_requests_snapshot = 0
stage_failures_snapshot = 0

# Global tracking for error codes and audio lengths
error_code_tracker = defaultdict(int)
audio_length_tracker = []
stage_error_codes = defaultdict(lambda: defaultdict(int))
stage_audio_lengths = defaultdict(list)


class StagesShapeWithMetrics(LoadTestShape):
    """
    Load shape with per-stage metrics tracking for Speaker Diarization
    """

    stages = [
        # Stage 1: Warm-up - Gentle start
        {"duration": 120, "users": 5, "spawn_rate": 1, "name": "Stage 1: Warm-up (5 users)"},

        # Stage 2: Baseline - Establish stable performance
        {"duration": 240, "users": 5, "spawn_rate": 1, "name": "Stage 2: Baseline (5 users)"}

        # # Stage 3: Light stress - Gradual increase
        # {"duration": 360, "users": 10, "spawn_rate": 1, "name": "Stage 3: Light Stress (10 users)"},

        # # Stage 4: Medium load - Hold and observe
        # {"duration": 480, "users": 10, "spawn_rate": 1, "name": "Stage 4: Medium Load Hold (10 users)"},

        # # Stage 5: Heavy stress - Push harder
        # {"duration": 600, "users": 20, "spawn_rate": 2, "name": "Stage 5: Heavy Stress (20 users)"},

        # # Stage 6: Peak load - Hold at high load
        # {"duration": 720, "users": 20, "spawn_rate": 2, "name": "Stage 6: Peak Load Hold (20 users)"},

        # # Stage 7: Breaking point - Push to failure
        # {"duration": 840, "users": 30, "spawn_rate": 2, "name": "Stage 7: Breaking Point (30 users)"},

        # # Stage 8: Observation - Watch it fail
        # {"duration": 960, "users": 30, "spawn_rate": 2, "name": "Stage 8: Failure Observation (30 users)"},

        # # Stage 9: Cool down - Scale back down
        # {"duration": 1020, "users": 5, "spawn_rate": 3, "name": "Stage 9: Cool Down (5 users)"},
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


def calculate_audio_length(audio_base64: str) -> float:
    """
    Estimate audio length in seconds from base64 encoded audio.
    Assumes WAV format with standard 16kHz sampling rate.
    """
    try:
        # Decode base64 to get byte size
        audio_bytes = base64.b64decode(audio_base64)
        audio_size_bytes = len(audio_bytes)

        # WAV file estimation:
        # Typical WAV: 16-bit (2 bytes), mono (1 channel), 16kHz sampling rate
        # Bytes per second = sample_rate * bytes_per_sample * channels
        # For 16kHz, 16-bit, mono: 16000 * 2 * 1 = 32000 bytes/sec

        # Subtract WAV header (typically 44 bytes)
        data_size = audio_size_bytes - 44 if audio_size_bytes > 44 else audio_size_bytes

        # Calculate duration in seconds
        bytes_per_second = 32000  # 16kHz * 2 bytes * 1 channel
        duration_seconds = data_size / bytes_per_second

        return round(duration_seconds, 2)
    except Exception as e:
        # If calculation fails, return 0
        return 0.0


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, context, **kwargs):
    """Track error codes and audio lengths per request"""
    global error_code_tracker, audio_length_tracker, stage_error_codes, stage_audio_lengths, current_stage_name

    # Track error codes
    if exception:
        # Exception occurred
        error_code = "EXCEPTION"
        error_code_tracker[error_code] += 1
        if current_stage_name:
            stage_error_codes[current_stage_name][error_code] += 1
    elif hasattr(context, 'response') and context.response:
        status_code = context.response.status_code
        if status_code >= 400:
            error_code = f"HTTP_{status_code}"
            error_code_tracker[error_code] += 1
            if current_stage_name:
                stage_error_codes[current_stage_name][error_code] += 1

    # Track audio length if available in context
    if hasattr(context, 'audio_content') and context.audio_content:
        audio_length = calculate_audio_length(context.audio_content)
        if audio_length > 0:
            audio_length_tracker.append(audio_length)
            if current_stage_name:
                stage_audio_lengths[current_stage_name].append(audio_length)


def capture_stage_metrics(shape_instance, stage_name: str, start_time: float):
    """Capture metrics for the completed stage"""
    global stage_metrics, stage_requests_snapshot, stage_failures_snapshot
    global stage_error_codes, stage_audio_lengths

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

    # Get error code distribution for this stage
    stage_error_code_dist = dict(stage_error_codes.get(stage_name, {}))

    # Get audio length statistics for this stage
    stage_audio_data = stage_audio_lengths.get(stage_name, [])
    audio_stats = calculate_audio_stats(stage_audio_data)

    # Get current response time stats (these are cumulative, but give us an idea)
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
        "error_codes": {
            "distribution": stage_error_code_dist,
            "top_errors": sorted(stage_error_code_dist.items(), key=lambda x: x[1], reverse=True)[:5]
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
        },
        "audio_analysis": audio_stats
    }

    stage_metrics[stage_name] = metrics

    # Print stage summary
    print(f"\n{'─'*70}")
    print(f"📊 {stage_name} - COMPLETED")
    print(f"Duration: {duration:.0f}s | Requests: {stage_requests} | Failures: {stage_failures}")
    print(f"Success Rate: {stage_success_rate:.2f}% | Error Rate: {stage_error_rate:.2f}%")
    print(f"Latency - Avg: {stats.avg_response_time:.0f}ms | P95: {stats.get_response_time_percentile(0.95):.0f}ms | P99: {stats.get_response_time_percentile(0.99):.0f}ms")
    print(f"Throughput: {stage_requests / duration:.2f} req/s")
    if audio_stats.get("count", 0) > 0:
        print(f"Audio Length - Avg: {audio_stats['average_seconds']:.2f}s | Total: {audio_stats['total_seconds']:.2f}s")
    print(f"{'─'*70}\n")


def calculate_audio_stats(audio_lengths: List[float]) -> Dict[str, Any]:
    """Calculate audio length statistics"""
    if not audio_lengths:
        return {
            "count": 0,
            "total_seconds": 0.0,
            "average_seconds": 0.0,
            "min_seconds": 0.0,
            "max_seconds": 0.0,
            "median_seconds": 0.0
        }

    sorted_lengths = sorted(audio_lengths)
    count = len(sorted_lengths)
    total = sum(sorted_lengths)

    return {
        "count": count,
        "total_seconds": round(total, 2),
        "average_seconds": round(total / count, 2),
        "min_seconds": round(sorted_lengths[0], 2),
        "max_seconds": round(sorted_lengths[-1], 2),
        "median_seconds": round(sorted_lengths[count // 2], 2)
    }


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Save detailed per-stage results to JSON"""
    global stage_metrics, error_code_tracker, audio_length_tracker

    # Only save on master (not on workers in distributed mode)
    if isinstance(environment.runner, WorkerRunner):
        return

    print("\n" + "="*70)
    print("📊 SPEAKER DIARIZATION LOAD SHAPE TEST COMPLETED")
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
    print(f"Overall Success Rate: {((stats.num_requests - stats.num_failures) / stats.num_requests * 100):.2f}%")
    print(f"Overall Error Rate: {(stats.num_failures / stats.num_requests * 100):.2f}%")

    # Print top error codes
    if error_code_tracker:
        print(f"\n🔍 TOP ERROR CODES:")
        sorted_errors = sorted(error_code_tracker.items(), key=lambda x: x[1], reverse=True)[:5]
        for error_code, count in sorted_errors:
            percentage = (count / stats.num_requests * 100) if stats.num_requests > 0 else 0
            print(f"   {error_code}: {count} ({percentage:.2f}%)")

    # Analyze breaking point
    print(f"\n🎯 CAPACITY ANALYSIS:")
    breaking_point = analyze_breaking_point(stage_metrics)
    if breaking_point:
        print(f"Breaking Point: {breaking_point['stage']}")
        print(f"Max Healthy Load: ~{breaking_point['max_users']} concurrent users")
        print(f"Recommendation: Run production with max {breaking_point['recommended_users']} users")

    # Build comprehensive JSON output
    output = build_enhanced_json_output(environment, stage_metrics, error_code_tracker, audio_length_tracker)

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

            # Define healthy thresholds for speaker diarization
            # Speaker diarization is compute-intensive, so allow higher latency
            is_healthy = error_rate < 5 and avg_latency < 30000  # <5% errors, <30s latency

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


def build_enhanced_json_output(environment, stage_metrics: Dict, error_codes: Dict, audio_lengths: List[float]) -> Dict[str, Any]:
    """Build comprehensive JSON output with per-stage metrics and error analysis"""
    stats = environment.stats.total

    # Get test configuration
    from dotenv import load_dotenv
    load_dotenv(override=True)
    config = SpeakerDiarizationConfig()

    # Calculate overall audio statistics
    overall_audio_stats = calculate_audio_stats(audio_lengths)

    # Prepare error code distribution for pie chart
    total_errors = sum(error_codes.values())
    error_distribution = {
        "by_code": dict(error_codes),
        "pie_chart_data": [
            {"error_code": code, "count": count, "percentage": round((count / total_errors * 100), 2)}
            for code, count in sorted(error_codes.items(), key=lambda x: x[1], reverse=True)
        ] if total_errors > 0 else []
    }

    # Overall statistics
    overall_stats = {
        "test_info": {
            "test_type": "load_shaping",
            "service": "Speaker Diarization",
            "service_id": config.service_id,
            "test_date": datetime.now().isoformat(),
            "total_duration_seconds": time.time() - environment.stats.start_time,
        },
        "test_config": {
            "service_id": config.service_id,
            "endpoint": "/services/inference/speaker-diarization"
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
            },
            "overall_audio_analysis": overall_audio_stats
        },
        "error_analysis": {
            "total_errors": total_errors,
            "error_distribution": error_distribution,
            "top_5_errors": sorted(error_codes.items(), key=lambda x: x[1], reverse=True)[:5]
        },
        "stage_by_stage_metrics": stage_metrics,
        "capacity_analysis": analyze_capacity(stage_metrics),
        "recommendations": generate_recommendations(stage_metrics),
        "grafana_metrics_summary": {
            "service_name": "speaker-diarization",
            "error_rate": {
                "overall_average_percentage": round((stats.num_failures / stats.num_requests * 100), 2) if stats.num_requests > 0 else 0,
                "by_service": {
                    config.service_id: round((stats.num_failures / stats.num_requests * 100), 2) if stats.num_requests > 0 else 0
                },
                "top_error_codes": error_distribution["pie_chart_data"]
            },
            "latency": {
                "overall_average_ms": round(stats.avg_response_time, 2),
                "by_service": {
                    config.service_id: round(stats.avg_response_time, 2)
                }
            },
            "payload": {
                "overall_average_audio_length_seconds": overall_audio_stats.get("average_seconds", 0.0),
                "by_service": {
                    config.service_id: overall_audio_stats.get("average_seconds", 0.0)
                },
                "total_audio_processed_seconds": overall_audio_stats.get("total_seconds", 0.0)
            }
        }
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

        # Classify stage health (adjusted thresholds for speaker diarization)
        if error_rate < 1 and p95_latency < 30000:  # <1% errors, <30s P95
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
        elif error_rate < 10 and p95_latency < 60000:  # <10% errors, <60s P95
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

    # Check latency issues (speaker diarization can take longer)
    for stage_name, metrics in stage_metrics.items():
        if metrics["latency_ms"]["p99"] > 60000:  # P99 > 60s
            recommendations["optimization_priority"].append(f"High P99 latency in {stage_name} - optimize response time")
            break

    if not recommendations["optimization_priority"]:
        recommendations["optimization_priority"].append("System performing well within tested range")

    return recommendations


def save_enhanced_results(output: Dict[str, Any]):
    """Save enhanced results to JSON file"""
    # Determine save path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    results_dir = os.path.join(parent_dir, "load_testing_shape_results")
    os.makedirs(results_dir, exist_ok=True)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(results_dir, f"speaker_diarization_load_shape_results_{timestamp}.json")

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

    # Print Grafana metrics summary
    grafana = output.get("grafana_metrics_summary", {})
    print(f"\n📊 Grafana Dashboard Metrics:")
    print(f"   Error Rate: {grafana.get('error_rate', {}).get('overall_average_percentage', 0)}%")
    print(f"   Average Latency: {grafana.get('latency', {}).get('overall_average_ms', 0)}ms")
    print(f"   Average Audio Length: {grafana.get('payload', {}).get('overall_average_audio_length_seconds', 0)}s")


class ConservativeShapeWithMetrics(LoadTestShape):
    """
    Very conservative load shape with metrics - for severely struggling servers.
    Increases load very slowly to find exact breaking point.

    Total duration: 12 minutes
    """

    stages = [
        {"duration": 60, "users": 2, "spawn_rate": 1, "name": "Stage 1: 2 users"},
        {"duration": 180, "users": 2, "spawn_rate": 1, "name": "Stage 1 Hold"},

        {"duration": 240, "users": 3, "spawn_rate": 1, "name": "Stage 2: 3 users"},
        {"duration": 360, "users": 3, "spawn_rate": 1, "name": "Stage 2 Hold"},

        {"duration": 420, "users": 5, "spawn_rate": 1, "name": "Stage 3: 5 users"},
        {"duration": 540, "users": 5, "spawn_rate": 1, "name": "Stage 3 Hold"},

        {"duration": 600, "users": 8, "spawn_rate": 1, "name": "Stage 4: 8 users"},
        {"duration": 720, "users": 8, "spawn_rate": 1, "name": "Stage 4 Hold"},
    ]

    def tick(self):
        global current_stage_name, stage_start_time, stage_requests_snapshot, stage_failures_snapshot

        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                # Check if entering new stage
                if current_stage_name != stage["name"]:
                    # Save metrics for previous stage
                    if current_stage_name is not None:
                        capture_stage_metrics(self, current_stage_name, stage_start_time)

                    # Start new stage
                    current_stage_name = stage["name"]
                    stage_start_time = time.time()

                    # Snapshot current metrics
                    if hasattr(self, 'runner') and self.runner:
                        stats = self.runner.stats.total
                        stage_requests_snapshot = stats.num_requests
                        stage_failures_snapshot = stats.num_failures

                    # Print stage announcement
                    print(f"\n{'='*70}")
                    print(f"STAGE: {stage['name']}")
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


class AggressiveShapeWithMetrics(LoadTestShape):
    """
    Aggressive load shape with metrics - for finding limits quickly.
    Rapidly increases load to find breaking point fast.

    Total duration: 10 minutes
    """

    stages = [
        {"duration": 60, "users": 5, "spawn_rate": 2, "name": "Quick Start"},
        {"duration": 150, "users": 5, "spawn_rate": 2, "name": "Quick Start Hold"},

        {"duration": 210, "users": 15, "spawn_rate": 3, "name": "Rapid Ramp"},
        {"duration": 300, "users": 15, "spawn_rate": 3, "name": "Rapid Hold"},

        {"duration": 360, "users": 30, "spawn_rate": 5, "name": "Heavy Push"},
        {"duration": 450, "users": 30, "spawn_rate": 5, "name": "Heavy Hold"},

        {"duration": 510, "users": 50, "spawn_rate": 10, "name": "Breaking Point"},
        {"duration": 600, "users": 50, "spawn_rate": 10, "name": "Observation"},
    ]

    def tick(self):
        global current_stage_name, stage_start_time, stage_requests_snapshot, stage_failures_snapshot

        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                # Check if entering new stage
                if current_stage_name != stage["name"]:
                    # Save metrics for previous stage
                    if current_stage_name is not None:
                        capture_stage_metrics(self, current_stage_name, stage_start_time)

                    # Start new stage
                    current_stage_name = stage["name"]
                    stage_start_time = time.time()

                    # Snapshot current metrics
                    if hasattr(self, 'runner') and self.runner:
                        stats = self.runner.stats.total
                        stage_requests_snapshot = stats.num_requests
                        stage_failures_snapshot = stats.num_failures

                    # Print stage announcement
                    print(f"\n{'='*70}")
                    print(f"STAGE: {stage['name']}")
                    print(f"Time: {run_time:.0f}s | Target Users: {stage['users']}")
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


# Default load shape - comment/uncomment to switch between shapes
# Use StagesShapeWithMetrics for normal capacity testing (recommended, ~17 min)
class CustomLoadShape(StagesShapeWithMetrics):
    pass

# Or use ConservativeShapeWithMetrics if server is very weak (~12 min)
# class CustomLoadShape(ConservativeShapeWithMetrics):
#     pass

# Or use AggressiveShapeWithMetrics to find limits quickly (~10 min)
# class CustomLoadShape(AggressiveShapeWithMetrics):
#     pass


if __name__ == "__main__":
    print("\n" + "="*70)
    print("Speaker Diarization Load Shape Testing with Enhanced Metrics")
    print("="*70)
    print("\nThis script captures detailed per-stage metrics:")
    print("  ✓ Error rate per stage (overall & by service)")
    print("  ✓ Error code distribution (pie chart data)")
    print("  ✓ Latency (min, max, median, avg, P95, P99) per stage")
    print("  ✓ Audio length analysis (avg, total seconds)")
    print("  ✓ Payload size per stage")
    print("  ✓ Throughput per stage")
    print("  ✓ Capacity analysis")
    print("  ✓ Breaking point detection")
    print("  ✓ Production recommendations")
    print("  ✓ Grafana dashboard metrics summary")
    print("\nTo run this test:")
    print("  locust -f Load_testing_DPG/load_testing_by_shape/speaker_diarization_load_shape_test_with_metrics.py --host=http://13.204.164.186:8000")
    print("\nResults will be saved to:")
    print("  Load_testing_DPG/load_testing_shape_results/speaker_diarization_load_shape_results_TIMESTAMP.json")
    print("="*70 + "\n")
