"""
Visualize timing breakdown from multiple NMT requests
Usage: ENV=sandbox python testing/AI4I/loadtesting/visualize_timing.py --requests 100
"""
import os
import argparse
import requests
import time
import statistics
from dotenv import load_dotenv
from collections import defaultdict

def parse_args():
    parser = argparse.ArgumentParser(description='Analyze NMT timing breakdown')
    parser.add_argument('--requests', type=int, default=50, help='Number of requests to analyze')
    return parser.parse_args()

def main():
    args = parse_args()

    env = os.getenv("ENV", "staging")
    load_dotenv(f"testing/.{env}.env", override=True)

    base_url = os.getenv("BASE_URL")

    print(f"\n{'='*80}")
    print(f"NMT Timing Analysis - {env.upper()} environment")
    print(f"Analyzing {args.requests} requests...")
    print(f"{'='*80}\n")

    # Login
    login_response = requests.post(
        f"{base_url}/api/v1/auth/login",
        json={
            "email": os.getenv("TEST_ACCOUNT_EMAIL_PATTERN", "ltest_user_{}@test.com").format(1),
            "password": os.getenv("TEST_ACCOUNT_PASSWORD", "Password@123"),
            "remember_me": False
        }
    )

    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        return

    access_token = login_response.json()["access_token"]
    print("✅ Login successful\n")

    # Prepare request
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "input": [{"source": "नमस्ते, आप कैसे हैं? मैं अच्छा हूं।"}],
        "config": {
            "serviceId": os.getenv("NMT_SERVICE_ID"),
            "language": {
                "sourceLanguage": "hi",
                "targetLanguage": "en"
            }
        },
        "controlConfig": {"additionalProp1": {"dataTracking": False}}
    }

    # Collect timing data
    timings = defaultdict(list)
    server_headers = defaultdict(list)
    success_count = 0

    print(f"Making {args.requests} requests", end='', flush=True)

    for i in range(args.requests):
        if i % 10 == 0:
            print('.', end='', flush=True)

        try:
            start = time.perf_counter()
            response = requests.post(
                f"{base_url}/api/v1/nmt/inference",
                headers=headers,
                json=payload,
                timeout=120
            )
            total_time = time.perf_counter() - start

            if response.status_code == 200:
                success_count += 1

                # Client-side timing
                timings['total'].append(total_time)
                timings['ttfb'].append(response.elapsed.total_seconds())

                # Check for server timing headers
                for header, value in response.headers.items():
                    if any(keyword in header.lower() for keyword in
                           ['time', 'timing', 'duration', 'inference', 'process']):
                        try:
                            # Try to parse as float (could be in seconds or ms)
                            num_value = float(value)
                            server_headers[header].append(num_value)
                        except ValueError:
                            # Store as string if not numeric
                            if header not in server_headers:
                                server_headers[header] = value

        except Exception as e:
            print(f"\n❌ Request {i+1} failed: {e}")

    print(f"\n\n✅ Completed: {success_count}/{args.requests} successful\n")

    if not timings['total']:
        print("❌ No successful requests to analyze")
        return

    # Display results
    print(f"{'='*80}")
    print("CLIENT-SIDE TIMING BREAKDOWN")
    print(f"{'='*80}\n")

    def print_stats(label, values):
        if not values:
            return
        print(f"{label:30s}  min={min(values):6.3f}s  avg={statistics.mean(values):6.3f}s  "
              f"p95={sorted(values)[int(len(values)*0.95)]:6.3f}s  max={max(values):6.3f}s")

    print_stats("Total Response Time", timings['total'])
    print_stats("TTFB (Server Processing)", timings['ttfb'])

    # Network overhead = total - ttfb
    network_overhead = [t - s for t, s in zip(timings['total'], timings['ttfb'])]
    print_stats("Network Overhead", network_overhead)

    # Server-side timings
    if server_headers:
        print(f"\n{'='*80}")
        print("SERVER-SIDE TIMING HEADERS")
        print(f"{'='*80}\n")

        inference_times = None

        for header, values in server_headers.items():
            if isinstance(values, list) and values:
                print_stats(header, values)

                # Track inference time for later calculation
                if 'inference' in header.lower():
                    inference_times = values
            else:
                print(f"{header:30s}  {values}")

        # Calculate non-inference server time
        if inference_times and len(inference_times) == len(timings['ttfb']):
            print(f"\n{'='*80}")
            print("CALCULATED NON-INFERENCE TIME")
            print(f"{'='*80}\n")

            # Detect if inference time is in ms (typically > 100) or seconds (typically < 10)
            avg_inference = statistics.mean(inference_times)
            if avg_inference > 50:  # Likely in milliseconds
                inference_times = [t / 1000 for t in inference_times]
                print(f"(Converted inference times from ms to seconds)\n")

            non_inference = [ttfb - inf for ttfb, inf in zip(timings['ttfb'], inference_times)]

            print_stats("Inference Time", inference_times)
            print_stats("Non-Inference Server Time", non_inference)

            print(f"\n{'='*80}")
            print("BREAKDOWN SUMMARY")
            print(f"{'='*80}\n")

            avg_total = statistics.mean(timings['total'])
            avg_network = statistics.mean(network_overhead)
            avg_inference = statistics.mean(inference_times)
            avg_non_inference = statistics.mean(non_inference)

            print(f"Average Total Time:        {avg_total:.3f}s (100.0%)")
            print(f"  ├─ Network Overhead:     {avg_network:.3f}s ({avg_network/avg_total*100:5.1f}%)")
            print(f"  └─ Server Processing:    {avg_total-avg_network:.3f}s ({(avg_total-avg_network)/avg_total*100:5.1f}%)")
            print(f"      ├─ Inference:        {avg_inference:.3f}s ({avg_inference/avg_total*100:5.1f}%)")
            print(f"      └─ Non-Inference:    {avg_non_inference:.3f}s ({avg_non_inference/avg_total*100:5.1f}%)")
            print(f"          (auth, validation, pre/post-processing)\n")

            print(f"💡 To exclude inference from your load tests, focus on:")
            print(f"   • Network overhead:     ~{avg_network:.3f}s")
            print(f"   • Non-inference server: ~{avg_non_inference:.3f}s")
            print(f"   • Combined:             ~{avg_network + avg_non_inference:.3f}s")
            print(f"   • This is {(avg_network + avg_non_inference)/avg_total*100:.1f}% of total request time\n")
    else:
        print(f"\n⚠️  No server timing headers found in response")
        print(f"    The API may not expose inference time breakdown")
        print(f"    TTFB ({statistics.mean(timings['ttfb']):.3f}s avg) represents total server processing\n")

if __name__ == "__main__":
    main()
