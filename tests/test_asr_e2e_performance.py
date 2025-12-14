"""
Automated E2E Performance Tests for ASR
Industry-standard approach using Pytest + Playwright
"""

import pytest
import json
import time
from datetime import datetime
from playwright.sync_api import sync_playwright, Page
import pandas as pd
from pathlib import Path

class TestASRPerformance:
    """E2E Performance Test Suite for ASR"""

    @pytest.fixture(scope="session")
    def browser_context(self):
        """Setup browser with HAR recording"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)  # Headless for CI/CD
            context = browser.new_context(
                record_har_path="test_results/asr_e2e.har",
                record_har_content="embed"
            )
            yield context
            context.close()
            browser.close()

    @pytest.fixture
    def asr_page(self, browser_context):
        """Navigate to ASR page (with login)"""
        page = browser_context.new_page()

        # Login
        page.goto("https://core-v1.ai4inclusion.org/login")
        page.fill("#username", "test-user@example.com")  # From env var in production
        page.fill("#password", "test-password")
        page.click("button[type='submit']")
        page.wait_for_load_state("networkidle")

        # Navigate to ASR
        page.goto("https://core-v1.ai4inclusion.org/asr")
        page.wait_for_load_state("networkidle")

        yield page
        page.close()

    def test_asr_small_file_performance(self, asr_page):
        """Test ASR performance with small audio file (<10s)"""

        start_time = time.time()

        # Upload file
        asr_page.set_input_files(
            "input[type='file']",
            "test_data/audio_samples/small_5sec.wav"
        )

        # Wait for transcript
        asr_page.wait_for_selector(
            ".transcript-content",
            timeout=30000,
            state="visible"
        )

        elapsed_ms = (time.time() - start_time) * 1000

        # Assertions
        assert elapsed_ms < 10000, f"Small file took {elapsed_ms}ms (expected <10s)"

        # Log metrics
        self._log_metric("small_file_e2e_time_ms", elapsed_ms)

        print(f"✅ Small file E2E: {elapsed_ms:.2f}ms")

    def test_asr_medium_file_performance(self, asr_page):
        """Test ASR performance with medium audio file (30s)"""

        start_time = time.time()

        asr_page.set_input_files(
            "input[type='file']",
            "test_data/audio_samples/medium_30sec.wav"
        )

        asr_page.wait_for_selector(
            ".transcript-content",
            timeout=60000,
            state="visible"
        )

        elapsed_ms = (time.time() - start_time) * 1000

        assert elapsed_ms < 35000, f"Medium file took {elapsed_ms}ms (expected <35s)"

        self._log_metric("medium_file_e2e_time_ms", elapsed_ms)

        print(f"✅ Medium file E2E: {elapsed_ms:.2f}ms")

    def test_asr_accuracy_validation(self, asr_page):
        """Validate ASR accuracy along with timing"""

        asr_page.set_input_files(
            "input[type='file']",
            "test_data/audio_samples/known_text.wav"
        )

        asr_page.wait_for_selector(".transcript-content", timeout=60000)

        # Get transcript
        transcript = asr_page.text_content(".transcript-content")
        expected_text = "hello world this is a test"

        # Simple accuracy check (you can use WER calculation)
        assert expected_text.lower() in transcript.lower(), \
            f"Transcript doesn't match: {transcript}"

        print(f"✅ Accuracy validated: {transcript}")

    def _log_metric(self, metric_name, value):
        """Log metric to file for tracking"""
        Path("test_results").mkdir(exist_ok=True)

        metric_data = {
            "timestamp": datetime.now().isoformat(),
            "metric": metric_name,
            "value": value,
            "test_run_id": datetime.now().strftime("%Y%m%d_%H%M%S")
        }

        # Append to metrics file
        with open("test_results/metrics.jsonl", "a") as f:
            f.write(json.dumps(metric_data) + "\n")


@pytest.fixture(scope="session", autouse=True)
def analyze_results():
    """Analyze HAR and generate report after all tests"""
    yield

    # After all tests complete
    print("\n" + "="*80)
    print("📊 ANALYZING TEST RESULTS")
    print("="*80)

    try:
        with open("test_results/asr_e2e.har", "r") as f:
            har_data = json.load(f)

        entries = har_data['log']['entries']

        # Analyze API calls
        api_calls = []
        for entry in entries:
            if '/api/' in entry['request']['url']:
                timings = entry['timings']
                api_calls.append({
                    'url': entry['request']['url'],
                    'method': entry['request']['method'],
                    'status': entry['response']['status'],
                    'wait_ms': timings.get('wait', 0),
                    'total_ms': entry['time']
                })

        if api_calls:
            df = pd.DataFrame(api_calls)
            print("\n🌐 API Call Summary:")
            print(df.to_string())

            # Export
            df.to_csv("test_results/api_timing.csv", index=False)
            print("\n✅ Results saved to test_results/")

    except Exception as e:
        print(f"⚠️  Could not analyze HAR: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
