"""
All Services Round-Robin Load Testing with Per-Service Metrics

This script tests all 10 services in round-robin rotation (ASR → NMT → TTS → ... → repeat)
during a single load test session, capturing both overall and per-service metrics.

Services tested (in round-robin order):
1. ASR (Automatic Speech Recognition)
2. NMT (Neural Machine Translation)
3. TTS (Text-to-Speech)
4. NER (Named Entity Recognition)
5. OCR (Optical Character Recognition)
6. Transliteration
7. TLD (Target Language Detection)
8. Speaker Diarization
9. Language Diarization
10. Audio Language Detection

Usage:
    locust -f Load_testing_DPG/load_testing_by_shape/all_services_load_shape.py --host=http://13.204.164.186:8000

Output:
    - Real-time metrics in console
    - Per-service metrics in JSON output
    - Overall aggregate metrics across all services
    - Error code distribution per service
    - Audio/text payload length analysis per service
"""

from locust import LoadTestShape, events, HttpUser, task, between
from locust.runners import WorkerRunner
import time
import json
import os
import base64
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict

# Import all service configurations
from shape_config import (
    ASRConfig, NMTConfig, TTSConfig, NERConfig,
    OCRConfig, TransliterationConfig, TLDConfig,
    SpeakerDiarizationConfig, LanguageDiarizationConfig,
    AudioLanguageDetectionConfig
)

# Global tracking for per-service metrics
service_error_codes = defaultdict(lambda: defaultdict(int))
service_audio_lengths = defaultdict(list)
service_text_lengths = defaultdict(list)

# Overall tracking
overall_error_codes = defaultdict(int)
overall_audio_lengths = []
overall_text_lengths = []

# ============================================================================
# GLOBAL SHARED CONFIGS - Load once and share across all users
# ============================================================================

print("Loading service configurations...")
_SHARED_CONFIGS = {
    'ASR': ASRConfig(),
    'NMT': NMTConfig(),
    'TTS': TTSConfig(),
    'NER': NERConfig(),
    'OCR': OCRConfig(),
    'Transliteration': TransliterationConfig(),
    'TLD': TLDConfig(),
    'SpeakerDiarization': SpeakerDiarizationConfig(),
    'LanguageDiarization': LanguageDiarizationConfig(),
    'AudioLanguageDetection': AudioLanguageDetectionConfig(),
}
print(f"✓ Loaded {len(_SHARED_CONFIGS)} service configurations (shared across all users)")


# ============================================================================
# ALL SERVICES USER CLASS WITH ROUND-ROBIN ROTATION
# ============================================================================

class AllServicesUser(HttpUser):
    """
    Single user class that cycles through all services in round-robin fashion.
    Each request goes to the next service in sequence: ASR → NMT → TTS → ... → repeat
    """

    # Add wait time between requests to prevent CPU overload
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests

    def on_start(self):
        """Initialize rotation using shared configs"""
        # Use shared configurations instead of loading per-user
        self.configs = _SHARED_CONFIGS

        # Define service rotation order
        self.service_order = [
            'ASR',
            'NMT',
            'TTS',
            'NER',
            'OCR',
            'Transliteration',
            'TLD',
            'SpeakerDiarization',
            'LanguageDiarization',
            'AudioLanguageDetection'
        ]

        # Service endpoints mapping
        self.service_endpoints = {
            'ASR': '/services/inference/asr',
            'NMT': '/services/inference/translation',
            'TTS': '/services/inference/tts',
            'NER': '/services/inference/ner',
            'OCR': '/services/inference/ocr',
            'Transliteration': '/services/inference/transliteration',
            'TLD': '/services/inference/tld',
            'SpeakerDiarization': '/services/inference/speaker-diarization',
            'LanguageDiarization': '/services/inference/language-diarization',
            'AudioLanguageDetection': '/services/inference/audio-lang-detection'
        }

        # Service sample method names mapping
        self.sample_methods = {
            'ASR': 'get_random_audio_sample',
            'NMT': 'get_random_nmt_sample',
            'TTS': 'get_random_tts_sample',
            'NER': 'get_random_ner_sample',
            'OCR': 'get_random_ocr_sample',
            'Transliteration': 'get_random_transliteration_sample',
            'TLD': 'get_random_tld_sample',
            'SpeakerDiarization': 'get_random_speaker_diarization_sample',
            'LanguageDiarization': 'get_random_language_diarization_sample',
            'AudioLanguageDetection': 'get_random_ald_sample'
        }

        # Track current position in rotation
        self.current_index = 0

    @task
    def round_robin_request(self):
        """
        Make a request to the current service in rotation, then move to next service.
        This creates a round-robin pattern: ASR → NMT → TTS → ... → ASR → ...
        """
        # Get current service
        service_name = self.service_order[self.current_index]
        config = self.configs[service_name]
        endpoint = self.service_endpoints[service_name]

        # Get sample data using the correct method for this service
        method_name = self.sample_methods[service_name]
        sample = getattr(config, method_name)()

        # Build payload - handle special cases for NER and OCR which require language parameter
        if service_name == 'NER':
            source_text = sample.get("source", "")
            language = sample.get("language", "hi")
            payload = config.build_payload(source_text, language)
            sample_data = source_text  # For tracking
        elif service_name == 'OCR':
            image_content = sample.get("imageContent", "")
            language = sample.get("language", "hi")
            payload = config.build_payload(image_content, language)
            sample_data = image_content  # For tracking
        else:
            payload = config.build_payload(sample)
            sample_data = sample  # For tracking

        # Make request with service name as the request name for Locust stats aggregation
        try:
            with self.client.post(
                endpoint,
                params={"serviceId": config.service_id},
                json=payload,
                headers=config.headers,
                catch_response=True,
                name=service_name  # This groups stats by service name
            ) as response:

                # Track payload data for metrics (simplified)
                if service_name in ['ASR', 'SpeakerDiarization', 'LanguageDiarization', 'AudioLanguageDetection']:
                    # Audio services - only calculate if needed for stats
                    audio_length = calculate_audio_length(sample_data)
                    if audio_length > 0:
                        service_audio_lengths[service_name].append(audio_length)
                        overall_audio_lengths.append(audio_length)
                elif service_name not in ['OCR']:  # Text services, skip OCR
                    text_length = len(sample_data) if isinstance(sample_data, str) else 0
                    if text_length > 0:
                        service_text_lengths[service_name].append(text_length)
                        overall_text_lengths.append(text_length)

                # Track errors
                if response.status_code >= 400:
                    error_code = f"HTTP_{response.status_code}"
                    service_error_codes[service_name][error_code] += 1
                    overall_error_codes[error_code] += 1
                    response.failure(f"HTTP {response.status_code}")
                else:
                    response.success()

        except Exception as e:
            error_code = "EXCEPTION"
            service_error_codes[service_name][error_code] += 1
            overall_error_codes[error_code] += 1

        # Move to next service in round-robin order
        self.current_index = (self.current_index + 1) % len(self.service_order)


# ============================================================================
# LOAD SHAPES - Multiple options for different server capacities
# ============================================================================

class StagesShapeWithMetrics(LoadTestShape):
    """
    Standard load shape with progressive stages - for normal capacity testing.
    Tests all services in round-robin rotation with increasing load.

    Total duration: ~17 minutes (9 stages)
    """

    stages = [
        # Stage 1: Warm-up - Gentle start
        {"duration": 120, "users": 5, "spawn_rate": 1, "name": "Stage 1: Warm-up (5 users)"},

        # Stage 2: Baseline - Establish stable performance
        {"duration": 240, "users": 5, "spawn_rate": 1, "name": "Stage 2: Baseline (5 users)"},

        # Stage 3: Light stress - Gradual increase
        {"duration": 360, "users": 10, "spawn_rate": 1, "name": "Stage 3: Light Stress (10 users)"},

        # Stage 4: Medium load - Hold and observe
        {"duration": 480, "users": 10, "spawn_rate": 1, "name": "Stage 4: Medium Load Hold (10 users)"},

        # Stage 5: Heavy stress - Push harder
        {"duration": 600, "users": 20, "spawn_rate": 2, "name": "Stage 5: Heavy Stress (20 users)"},

        # Stage 6: Peak load - Hold at high load
        {"duration": 720, "users": 20, "spawn_rate": 2, "name": "Stage 6: Peak Load Hold (20 users)"},

        # Stage 7: Breaking point - Push to failure
        {"duration": 840, "users": 30, "spawn_rate": 2, "name": "Stage 7: Breaking Point (30 users)"},

        # Stage 8: Observation - Watch it fail
        {"duration": 960, "users": 30, "spawn_rate": 2, "name": "Stage 8: Failure Observation (30 users)"},

        # Stage 9: Cool down - Scale back down
        {"duration": 1020, "users": 5, "spawn_rate": 3, "name": "Stage 9: Cool Down (5 users)"},
    ]

    def tick(self):
        """Returns (user_count, spawn_rate) for current time"""
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])

        # Test complete - auto-quit
        print(f"\n{'='*70}")
        print("✅ All stages completed - stopping test automatically...")
        print(f"{'='*70}\n")

        if hasattr(self, 'runner') and self.runner:
            self.runner.quit()

        return None


class ConservativeShapeWithMetrics(LoadTestShape):
    """
    Very conservative load shape - for weaker servers.
    Tests all services in round-robin rotation with gentle load increase.

    Total duration: ~12 minutes
    """

    stages = [
        {"duration": 60, "users": 1, "spawn_rate": 1, "name": "Stage 1: 1 users"},
        {"duration": 180, "users": 1, "spawn_rate": 1, "name": "Stage 1 Hold"},

        {"duration": 240, "users": 1, "spawn_rate": 1, "name": "Stage 2: 1 users"},
        {"duration": 360, "users": 1, "spawn_rate": 1, "name": "Stage 2 Hold"}

    #     {"duration": 420, "users": 5, "spawn_rate": 1, "name": "Stage 3: 5 users"},
    #     {"duration": 540, "users": 5, "spawn_rate": 1, "name": "Stage 3 Hold"},

    #     {"duration": 600, "users": 8, "spawn_rate": 1, "name": "Stage 4: 8 users"},
    #     {"duration": 720, "users": 8, "spawn_rate": 1, "name": "Stage 4 Hold"},
    ]

    def tick(self):
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])

        print(f"\n{'='*70}")
        print("✅ All stages completed - stopping test automatically...")
        print(f"{'='*70}\n")

        if hasattr(self, 'runner') and self.runner:
            self.runner.quit()

        return None


class AggressiveShapeWithMetrics(LoadTestShape):
    """
    Aggressive load shape - for finding limits quickly.
    Tests all services in round-robin rotation with rapid load increase.

    Total duration: ~10 minutes
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
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])

        print(f"\n{'='*70}")
        print("✅ All stages completed - stopping test automatically...")
        print(f"{'='*70}\n")

        if hasattr(self, 'runner') and self.runner:
            self.runner.quit()

        return None


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def calculate_audio_length(audio_base64: str) -> float:
    """Estimate audio length in seconds from base64 encoded audio"""
    try:
        audio_bytes = base64.b64decode(audio_base64)
        audio_size_bytes = len(audio_bytes)
        data_size = audio_size_bytes - 44 if audio_size_bytes > 44 else audio_size_bytes
        bytes_per_second = 32000  # 16kHz * 2 bytes * 1 channel
        duration_seconds = data_size / bytes_per_second
        return round(duration_seconds, 2)
    except:
        return 0.0


def calculate_stats(data: List[float], unit: str) -> Optional[Dict[str, Any]]:
    """Calculate statistics for a data list"""
    if not data:
        return None

    sorted_data = sorted(data)
    count = len(sorted_data)
    total = sum(sorted_data)

    return {
        "count": count,
        f"total_{unit}": round(total, 2),
        f"average_{unit}": round(total / count, 2),
        f"min_{unit}": round(sorted_data[0], 2),
        f"max_{unit}": round(sorted_data[-1], 2),
        f"median_{unit}": round(sorted_data[count // 2], 2)
    }


def get_service_stats(stats, service_name: str):
    """
    Get stats for a service by name, trying POST method first, then checking all entries.
    Returns None if service stats not found.
    """
    # Try POST method first (most common)
    try:
        service_stats = stats.get(service_name, "POST")
        if service_stats and service_stats.num_requests > 0:
            return service_stats
    except:
        pass

    # If not found, search through all entries
    for (name, method), entry in stats.entries.items():
        if name == service_name and entry.num_requests > 0:
            return entry

    return None


# ============================================================================
# TEST COMPLETION HANDLER
# ============================================================================

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Save comprehensive results with per-service and overall metrics"""
    global service_error_codes, service_audio_lengths, service_text_lengths
    global overall_error_codes, overall_audio_lengths, overall_text_lengths

    # Only save on master
    if isinstance(environment.runner, WorkerRunner):
        return

    print("\n" + "="*70)
    print("📊 ALL SERVICES ROUND-ROBIN LOAD TEST COMPLETED")
    print("="*70)

    stats = environment.stats
    total_stats = stats.total

    # Overall summary
    print(f"\n🔍 OVERALL TEST SUMMARY:")
    print(f"Total Requests: {total_stats.num_requests}")
    print(f"Total Failures: {total_stats.num_failures}")
    if total_stats.num_requests > 0:
        print(f"Overall Success Rate: {((total_stats.num_requests - total_stats.num_failures) / total_stats.num_requests * 100):.2f}%")
        print(f"Overall Error Rate: {(total_stats.num_failures / total_stats.num_requests * 100):.2f}%")
        print(f"Overall Avg Latency: {total_stats.avg_response_time:.2f}ms")

    # Per-service summary
    print(f"\n📊 PER-SERVICE SUMMARY:")
    service_names = ['ASR', 'NMT', 'TTS', 'NER', 'OCR', 'Transliteration', 'TLD',
                     'SpeakerDiarization', 'LanguageDiarization', 'AudioLanguageDetection']

    for service_name in service_names:
        service_stats = get_service_stats(stats, service_name)
        if service_stats and service_stats.num_requests > 0:
            success_rate = ((service_stats.num_requests - service_stats.num_failures) / service_stats.num_requests * 100)
            print(f"  {service_name:25s}: {service_stats.num_requests:4d} requests | "
                  f"{success_rate:5.1f}% success | {service_stats.avg_response_time:7.0f}ms avg latency")

    # Build comprehensive output
    output = build_comprehensive_output(environment, stats, service_error_codes,
                                       service_audio_lengths, service_text_lengths,
                                       overall_error_codes, overall_audio_lengths, overall_text_lengths)

    # Save to file
    save_results(output)

    print("="*70 + "\n")


def build_comprehensive_output(environment, stats, service_errors: Dict,
                               service_audio: Dict, service_text: Dict,
                               overall_errors: Dict, overall_audio: List,
                               overall_text: List) -> Dict[str, Any]:
    """Build comprehensive JSON output with overall and per-service metrics"""

    total_stats = stats.total

    # Calculate overall statistics
    overall_audio_stats = calculate_stats(overall_audio, "seconds")
    overall_text_stats = calculate_stats(overall_text, "characters")

    # Overall error distribution
    total_errors = sum(overall_errors.values())
    overall_error_distribution = {
        "by_code": dict(overall_errors),
        "pie_chart_data": [
            {"error_code": code, "count": count, "percentage": round((count / total_errors * 100), 2)}
            for code, count in sorted(overall_errors.items(), key=lambda x: x[1], reverse=True)
        ] if total_errors > 0 else []
    }

    # Build per-service metrics
    service_names = ['ASR', 'NMT', 'TTS', 'NER', 'OCR', 'Transliteration', 'TLD',
                     'SpeakerDiarization', 'LanguageDiarization', 'AudioLanguageDetection']

    per_service_metrics = {}
    grafana_by_service = {}

    for service_name in service_names:
        service_stats = get_service_stats(stats, service_name)

        if not service_stats or service_stats.num_requests == 0:
            continue

        # Service error rate
        service_error_rate = (service_stats.num_failures / service_stats.num_requests * 100) if service_stats.num_requests > 0 else 0

        # Service error distribution
        service_error_dict = dict(service_errors.get(service_name, {}))
        service_total_errors = sum(service_error_dict.values())
        service_error_pie = [
            {"error_code": code, "count": count, "percentage": round((count / service_total_errors * 100), 2)}
            for code, count in sorted(service_error_dict.items(), key=lambda x: x[1], reverse=True)
        ] if service_total_errors > 0 else []

        # Payload analysis
        audio_data = service_audio.get(service_name, [])
        text_data = service_text.get(service_name, [])

        payload_analysis = {}
        if audio_data:
            payload_analysis["audio_lengths"] = calculate_stats(audio_data, "seconds")
        if text_data:
            payload_analysis["text_lengths"] = calculate_stats(text_data, "characters")

        # Service metrics
        per_service_metrics[service_name] = {
            "requests": {
                "total": service_stats.num_requests,
                "successful": service_stats.num_requests - service_stats.num_failures,
                "failed": service_stats.num_failures,
                "success_rate_percentage": round(100 - service_error_rate, 2),
                "error_rate_percentage": round(service_error_rate, 2)
            },
            "error_codes": {
                "distribution": service_error_dict,
                "top_errors": sorted(service_error_dict.items(), key=lambda x: x[1], reverse=True)[:5]
            },
            "latency_ms": {
                "min": round(service_stats.min_response_time, 2),
                "max": round(service_stats.max_response_time, 2),
                "median": round(service_stats.median_response_time, 2),
                "average": round(service_stats.avg_response_time, 2),
                "p95": round(service_stats.get_response_time_percentile(0.95), 2),
                "p99": round(service_stats.get_response_time_percentile(0.99), 2)
            },
            "throughput": {
                "requests_per_second": round(service_stats.total_rps, 2)
            },
            "payload_analysis": payload_analysis
        }

        # Grafana metrics for this service
        payload_grafana = {}
        if audio_data:
            audio_stats = calculate_stats(audio_data, "seconds")
            payload_grafana["average_audio_length_seconds"] = audio_stats["average_seconds"]
            payload_grafana["total_audio_processed_seconds"] = audio_stats["total_seconds"]
        if text_data:
            text_stats = calculate_stats(text_data, "characters")
            payload_grafana["average_text_length_characters"] = text_stats["average_characters"]
            payload_grafana["total_text_processed_characters"] = text_stats["total_characters"]

        grafana_by_service[service_name] = {
            "error_rate": {
                "percentage": round(service_error_rate, 2),
                "top_error_codes": service_error_pie
            },
            "latency": {
                "average_ms": round(service_stats.avg_response_time, 2),
                "p95_ms": round(service_stats.get_response_time_percentile(0.95), 2),
                "p99_ms": round(service_stats.get_response_time_percentile(0.99), 2)
            },
            "payload": payload_grafana,
            "throughput": {
                "requests_per_second": round(service_stats.total_rps, 2)
            }
        }

    # Overall output structure
    output = {
        "test_info": {
            "test_type": "all_services_round_robin",
            "test_date": datetime.now().isoformat(),
            "total_duration_seconds": round(time.time() - environment.stats.start_time, 2),
            "services_tested": list(per_service_metrics.keys()),
            "services_count": len(per_service_metrics),
            "description": "All services tested in round-robin rotation (ASR → NMT → TTS → ...)"
        },
        "overall_statistics": {
            "total_requests": total_stats.num_requests,
            "failed_requests": total_stats.num_failures,
            "successful_requests": total_stats.num_requests - total_stats.num_failures,
            "success_rate_percentage": round(((total_stats.num_requests - total_stats.num_failures) / total_stats.num_requests * 100), 2) if total_stats.num_requests > 0 else 0,
            "error_rate_percentage": round((total_stats.num_failures / total_stats.num_requests * 100), 2) if total_stats.num_requests > 0 else 0,
            "overall_latency_ms": {
                "min": round(total_stats.min_response_time, 2),
                "max": round(total_stats.max_response_time, 2),
                "median": round(total_stats.median_response_time, 2),
                "average": round(total_stats.avg_response_time, 2),
                "p95": round(total_stats.get_response_time_percentile(0.95), 2),
                "p99": round(total_stats.get_response_time_percentile(0.99), 2)
            },
            "overall_throughput": {
                "total_rps": round(total_stats.total_rps, 2)
            },
            "overall_payload_analysis": {
                "audio": overall_audio_stats,
                "text": overall_text_stats
            }
        },
        "overall_error_analysis": {
            "total_errors": total_errors,
            "error_distribution": overall_error_distribution,
            "top_5_errors": sorted(overall_errors.items(), key=lambda x: x[1], reverse=True)[:5]
        },
        "per_service_metrics": per_service_metrics,
        "grafana_metrics_summary": {
            "overall": {
                "error_rate": {
                    "overall_average_percentage": round((total_stats.num_failures / total_stats.num_requests * 100), 2) if total_stats.num_requests > 0 else 0,
                    "top_error_codes": overall_error_distribution["pie_chart_data"]
                },
                "latency": {
                    "overall_average_ms": round(total_stats.avg_response_time, 2),
                    "p95_ms": round(total_stats.get_response_time_percentile(0.95), 2),
                    "p99_ms": round(total_stats.get_response_time_percentile(0.99), 2)
                },
                "payload": {
                    "audio": {
                        "average_length_seconds": overall_audio_stats["average_seconds"] if overall_audio_stats else 0,
                        "total_processed_seconds": overall_audio_stats["total_seconds"] if overall_audio_stats else 0
                    } if overall_audio_stats else None,
                    "text": {
                        "average_length_characters": overall_text_stats["average_characters"] if overall_text_stats else 0,
                        "total_processed_characters": overall_text_stats["total_characters"] if overall_text_stats else 0
                    } if overall_text_stats else None
                }
            },
            "by_service": grafana_by_service
        }
    }

    return output


def save_results(output: Dict[str, Any]):
    """Save results to JSON file"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    results_dir = os.path.join(parent_dir, "load_testing_shape_results")
    os.makedirs(results_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(results_dir, f"all_services_round_robin_results_{timestamp}.json")

    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Detailed results saved to: {filename}")
    print(f"\n📊 Summary:")
    print(f"   Services Tested: {output['test_info']['services_count']}")
    print(f"   Total Requests: {output['overall_statistics']['total_requests']}")
    print(f"   Overall Error Rate: {output['overall_statistics']['error_rate_percentage']}%")
    print(f"   Overall Average Latency: {output['overall_statistics']['overall_latency_ms']['average']}ms")

    # Print top 3 fastest and slowest services
    services_by_latency = sorted(
        output['per_service_metrics'].items(),
        key=lambda x: x[1]['latency_ms']['average']
    )

    if len(services_by_latency) >= 3:
        print(f"\n   Fastest Services:")
        for service_name, metrics in services_by_latency[:3]:
            print(f"      {service_name}: {metrics['latency_ms']['average']:.0f}ms avg")

        print(f"\n   Slowest Services:")
        for service_name, metrics in services_by_latency[-3:]:
            print(f"      {service_name}: {metrics['latency_ms']['average']:.0f}ms avg")


# ============================================================================
# LOAD SHAPE SELECTION
# ============================================================================

# IMPORTANT: Locust will use the class specified below as CustomLoadShape
# Only ONE CustomLoadShape should be active at a time

# Default load shape - comment/uncomment to switch between shapes

# Use StagesShapeWithMetrics for normal capacity testing (recommended, ~17 min)
# class CustomLoadShape(StagesShapeWithMetrics):
#     pass

# Or use ConservativeShapeWithMetrics if server is very weak (~12 min)
class CustomLoadShape(ConservativeShapeWithMetrics):
    pass

# Or use AggressiveShapeWithMetrics to find limits quickly (~10 min)
# class CustomLoadShape(AggressiveShapeWithMetrics):
#     pass

# Hide the base shape classes from Locust by prefixing with underscore
# This ensures Locust only sees CustomLoadShape
_StagesShapeWithMetrics = StagesShapeWithMetrics
_ConservativeShapeWithMetrics = ConservativeShapeWithMetrics
_AggressiveShapeWithMetrics = AggressiveShapeWithMetrics
del StagesShapeWithMetrics
del ConservativeShapeWithMetrics
del AggressiveShapeWithMetrics


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("All Services Round-Robin Load Testing")
    print("="*70)
    print(f"Active Load Shape: {CustomLoadShape.__name__}")
    print(f"Inherits from: {CustomLoadShape.__bases__[0].__name__}")
    if hasattr(CustomLoadShape, 'stages'):
        print(f"First stage: {CustomLoadShape.stages[0]}")
    print("="*70)
    print("\nThis script tests all 10 services in round-robin rotation:")
    print("  Each user cycles through: ASR → NMT → TTS → NER → OCR →")
    print("  Transliteration → TLD → SpeakerDiarization →")
    print("  LanguageDiarization → AudioLanguageDetection → repeat")
    print("\nAll services are tested concurrently throughout the load test.")
    print("\nMetrics captured:")
    print("  ✓ Per-service error rates, latency, throughput")
    print("  ✓ Per-service error code distribution (pie chart data)")
    print("  ✓ Per-service payload analysis (audio/text lengths)")
    print("  ✓ Overall aggregate metrics across all services")
    print("  ✓ Grafana dashboard metrics (overall + by service)")
    print("\nLoad Shape Options (change in code by commenting/uncommenting):")
    print("  • StagesShapeWithMetrics (default): 9 stages, ~17 min")
    print("  • ConservativeShapeWithMetrics: Gentle load, ~12 min")
    print("  • AggressiveShapeWithMetrics: Fast ramp-up, ~10 min")
    print("\nTo run this test:")
    print("  locust -f Load_testing_DPG/load_testing_by_shape/all_services_load_shape.py --host=http://13.204.164.186:8000")
    print("\nResults will be saved to:")
    print("  Load_testing_DPG/load_testing_shape_results/all_services_round_robin_results_TIMESTAMP.json")
    print("="*70 + "\n")
