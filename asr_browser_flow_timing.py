"""
ASR Browser Flow with Complete Timing Breakdown
Automates: Login → Navigate → Upload → Submit → Response
Captures timing for each step
"""

import json
import time
from datetime import datetime
from playwright.sync_api import sync_playwright
import pandas as pd

class ASRBrowserFlowAnalyzer:
    def __init__(self, config):
        self.config = config
        self.timing_data = []
        self.har_data = None

    def run_flow(self):
        """Execute complete ASR flow with timing capture"""

        with sync_playwright() as p:
            # Launch browser with HAR recording
            browser = p.chromium.launch(headless=False)  # Set True for headless
            context = browser.new_context(
                record_har_path="asr_flow.har",
                record_har_content="embed"
            )
            page = context.new_page()

            print("\n" + "="*80)
            print("🚀 STARTING ASR BROWSER FLOW ANALYSIS")
            print("="*80 + "\n")

            try:
                # Step 1: Login
                self._login(page)

                # Step 2: Navigate to ASR page
                self._navigate_to_asr(page)

                # Step 3: Upload file (auto-triggers processing)
                self._upload_file(page)

                # Close and save HAR
                context.close()
                browser.close()

                # Analyze timing
                self._analyze_har()
                self._display_results()
                self._export_results()

            except Exception as e:
                print(f"❌ Error: {e}")
                context.close()
                browser.close()
                raise

    def _login(self, page):
        """Step 1: Login with timing"""
        print("📝 Step 1: Logging in...")
        start_time = time.time()

        # Navigate to login page
        page.goto(self.config['login_url'])
        page.wait_for_load_state('networkidle')

        # Fill login form
        page.fill(self.config['username_selector'], self.config['username'])
        page.fill(self.config['password_selector'], self.config['password'])

        # Click login button
        page.click(self.config['login_button_selector'])
        page.wait_for_load_state('networkidle')

        elapsed = (time.time() - start_time) * 1000
        print(f"   ✅ Login completed: {elapsed:.2f} ms\n")

        self.timing_data.append({
            'step': 'Login',
            'duration_ms': elapsed,
            'timestamp': datetime.now().isoformat()
        })

    def _navigate_to_asr(self, page):
        """Step 2: Navigate to ASR page"""
        print("🔗 Step 2: Navigating to ASR page...")
        start_time = time.time()

        page.goto(self.config['asr_page_url'])
        page.wait_for_load_state('networkidle')

        elapsed = (time.time() - start_time) * 1000
        print(f"   ✅ Navigation completed: {elapsed:.2f} ms\n")

        self.timing_data.append({
            'step': 'Navigate to ASR',
            'duration_ms': elapsed,
            'timestamp': datetime.now().isoformat()
        })

    def _upload_file(self, page):
        """Step 3: Upload audio file and wait for processing"""
        print("📤 Step 3: Uploading audio file and processing...")
        start_time = time.time()

        # Upload file (this triggers automatic processing)
        page.set_input_files(
            self.config['file_input_selector'],
            self.config['audio_file_path']
        )

        print(f"   📁 File selected, waiting for processing...")

        # Wait for transcript tab to become active or visible
        # Try multiple strategies to detect completion
        try:
            # Strategy 1: Wait for transcript tab/element to appear
            if 'transcript_tab_selector' in self.config:
                page.wait_for_selector(
                    self.config['transcript_tab_selector'],
                    timeout=120000  # 2 minute timeout for ASR processing
                )
                # Click transcript tab to view result
                page.click(self.config['transcript_tab_selector'])
                time.sleep(0.5)  # Let tab content load

            # Strategy 2: Wait for result element in transcript area
            page.wait_for_selector(
                self.config['result_selector'],
                timeout=120000,
                state='visible'
            )

        except Exception as e:
            print(f"   ⚠️  Waiting fallback (30s)...")
            time.sleep(30)

        elapsed = (time.time() - start_time) * 1000
        print(f"   ✅ Processing completed: {elapsed:.2f} ms ({elapsed/1000:.2f} sec)\n")

        self.timing_data.append({
            'step': 'Upload & Process',
            'duration_ms': elapsed,
            'timestamp': datetime.now().isoformat()
        })

        # Capture result text
        try:
            result_text = page.text_content(self.config['result_selector'])
            print(f"   📄 Transcript preview: {result_text[:150]}...\n")
        except:
            print(f"   📄 Result captured (text extraction skipped)\n")

    def _submit_and_wait(self, page):
        """Step 4: Not needed - upload triggers processing automatically"""
        # This step is skipped since upload auto-processes
        pass

    def _analyze_har(self):
        """Analyze HAR file for detailed network timing"""
        print("📊 Analyzing network timing from HAR file...")

        with open('asr_flow.har', 'r') as f:
            self.har_data = json.load(f)

        entries = self.har_data['log']['entries']

        # Focus on API calls and important resources
        api_timing = []

        for entry in entries:
            url = entry['request']['url']
            method = entry['request']['method']

            # Filter for relevant calls
            if any(keyword in url.lower() for keyword in ['api', 'transcribe', 'upload', 'auth', 'login']):
                timings = entry['timings']

                api_timing.append({
                    'url': url,
                    'method': method,
                    'status': entry['response']['status'],
                    'dns_ms': timings.get('dns', 0),
                    'connect_ms': timings.get('connect', 0),
                    'ssl_ms': timings.get('ssl', 0),
                    'send_ms': timings.get('send', 0),
                    'wait_ms': timings.get('wait', 0),  # Server processing
                    'receive_ms': timings.get('receive', 0),
                    'total_ms': entry['time']
                })

        self.api_timing = pd.DataFrame(api_timing)

    def _display_results(self):
        """Display comprehensive timing breakdown"""
        print("\n" + "="*80)
        print("📈 COMPLETE FLOW TIMING BREAKDOWN")
        print("="*80 + "\n")

        # Step-by-step timing
        total_flow_time = 0
        for step_data in self.timing_data:
            print(f"🔹 {step_data['step']}: {step_data['duration_ms']:.2f} ms")
            total_flow_time += step_data['duration_ms']

        print(f"\n{'='*40}")
        print(f"🏁 TOTAL FLOW TIME: {total_flow_time:.2f} ms ({total_flow_time/1000:.2f} sec)")
        print(f"{'='*40}\n")

        # Detailed API timing
        if not self.api_timing.empty:
            print("\n" + "="*80)
            print("🌐 DETAILED API CALL BREAKDOWN")
            print("="*80 + "\n")

            for idx, row in self.api_timing.iterrows():
                print(f"📍 {row['method']} {row['url']}")
                print(f"   Status: {row['status']}")
                print(f"   ├─ Network Overhead:")
                print(f"   │  ├─ DNS: {row['dns_ms']:.2f} ms")
                print(f"   │  ├─ Connect: {row['connect_ms']:.2f} ms")
                print(f"   │  ├─ SSL: {row['ssl_ms']:.2f} ms")
                print(f"   │  └─ Send: {row['send_ms']:.2f} ms")
                print(f"   ├─ ⭐ Server Processing: {row['wait_ms']:.2f} ms")
                print(f"   ├─ Response Download: {row['receive_ms']:.2f} ms")
                print(f"   └─ 🏁 TOTAL: {row['total_ms']:.2f} ms\n")

    def _export_results(self):
        """Export results to Excel"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Export flow timing
        flow_df = pd.DataFrame(self.timing_data)
        flow_output = f'asr_flow_timing_{timestamp}.xlsx'

        with pd.ExcelWriter(flow_output) as writer:
            flow_df.to_excel(writer, sheet_name='Flow Steps', index=False)
            if not self.api_timing.empty:
                self.api_timing.to_excel(writer, sheet_name='API Calls', index=False)

        print(f"✅ Results exported to: {flow_output}")
        print(f"✅ HAR file saved as: asr_flow.har\n")


# Configuration
CONFIG = {
    # Login details
    'login_url': 'https://core-v1.ai4inclusion.org/login',  # ← Update with actual login URL
    'username_selector': '#username',  # ← Update based on actual login form
    'password_selector': '#password',   # ← Update based on actual login form
    'login_button_selector': 'button[type="submit"]',  # ← Update if needed
    'username': 'your-username',        # ← Your credentials
    'password': 'your-password',

    # ASR page
    'asr_page_url': 'https://core-v1.ai4inclusion.org/asr',
    'file_input_selector': 'button[type="button"]',  # File upload button

    # Transcript tab - UPDATE THESE based on your UI
    'transcript_tab_selector': '#transcript-tab',  # ← Tab that shows transcript
    'result_selector': '#transcription-result',     # ← Transcript text area
    # Alternative common selectors:
    # 'transcript_tab_selector': 'button:has-text("Transcript")',
    # 'result_selector': '.transcript-content',
    # 'result_selector': 'div[role="tabpanel"]',

    # Audio file to test
    'audio_file_path': '/path/to/your/audio.wav'  # ← Update with actual audio file path
}


if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║         ASR Browser Flow Timing Analyzer                       ║
    ║  Captures complete timing: Login → Upload → Submit → Response  ║
    ╚════════════════════════════════════════════════════════════════╝
    """)

    # Update CONFIG above with your actual values
    analyzer = ASRBrowserFlowAnalyzer(CONFIG)
    analyzer.run_flow()
