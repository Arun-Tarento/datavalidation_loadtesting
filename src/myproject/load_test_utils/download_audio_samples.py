#!/usr/bin/env python3
"""
Download audio files from Aikosha API, convert to base64 string, and save with text.

Output format: List of dict with {"audio_to_string": "base64...", "txt": "transcript"}

Usage:
    python download_audio_samples.py --limit 50 --api-key YOUR_API_KEY
"""

import asyncio
import httpx
import json
import base64
import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logger
try:
    logger.remove()
except Exception:
    pass

logger.add(
    sys.stdout,
    level="INFO",
    colorize=True,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{function}</cyan> - <level>{message}</level>",
)

SCRIPT_DIR = Path(__file__).parent.resolve()
OUTPUT_FILE = SCRIPT_DIR / "audio_samples_with_text.json"

# Aikosha API Configuration
API_BASE_URL = "https://aikosha-api.indiaai.gov.in/akp/idp/api/v1"
DATASET_IDENTIFIER = "tamil_asr_benchmark_dataset_kathbath_tamil_test_unknown"
FOLDER_PATH = "Bhashini/files/Kathbath-Tamil-Test-Unknown/audios"
VERSION_NUMBER = 1
REQUEST_TIMEOUT = 60.0
MAX_CONCURRENT = 5


class AudioSampleDownloader:
    """Download audio samples from Aikosha and convert to base64"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.stats = {
            "fetched": 0,
            "downloaded": 0,
            "failed": 0,
            "encoded": 0
        }

    def get_headers(self) -> Dict:
        """Get API headers for Aikosha"""
        return {
            "accept": "application/json",
            "access-key": self.api_key,
            "Content-Type": "application/json"
        }

    async def fetch_file_list(self, client: httpx.AsyncClient, limit: int, page: int = 1) -> List[Dict]:
        """Fetch audio file details from Aikosha API for a specific page"""
        try:
            logger.info(f"Fetching page {page} from Aikosha API (limit: {limit})...")

            payload = {
                "datasetIdentifier": DATASET_IDENTIFIER,
                "page": page,
                "versionNumber": VERSION_NUMBER,
                "limit": limit,
                "folderPath": FOLDER_PATH
            }

            response = await client.post(
                f"{API_BASE_URL}/dataset-public/file-details",
                json=payload,
                headers=self.get_headers(),
                timeout=REQUEST_TIMEOUT
            )

            if response.status_code == 200:
                resp_data = response.json()
                header = resp_data.get("header", {})

                # Check if request was successful
                if not header.get("success", False):
                    error_msg = header.get("msg", "Unknown error")
                    logger.warning(f"API returned error for page {page}: {error_msg}")
                    return []

                # The response has 'data' and 'header' keys
                data_section = resp_data.get("data")

                if data_section:
                    if isinstance(data_section, dict):
                        files = data_section.get("files", [])
                    elif isinstance(data_section, list):
                        # data might directly be a list of files
                        files = data_section
                    else:
                        files = []
                else:
                    files = []

                # Debug: Print first file structure if available (only for page 1)
                if files and page == 1:
                    logger.info(f"First file keys: {list(files[0].keys())}")
                    logger.info(f"First file sample: {json.dumps(files[0], indent=2)[:500]}")

                logger.success(f"✓ Fetched {len(files)} files from page {page}")
                return files
            else:
                logger.error(f"✗ Failed to fetch page {page}: {response.status_code}")
                logger.error(f"Response: {response.text[:500]}")
                return []

        except Exception as e:
            logger.error(f"✗ Exception fetching page {page}: {str(e)}")
            return []

    async def fetch_multiple_pages(self, client: httpx.AsyncClient, limit: int, num_pages: int) -> List[Dict]:
        """Fetch multiple pages of file details"""
        all_files = []

        for page in range(1, num_pages + 1):
            files = await self.fetch_file_list(client, limit, page)
            if files:
                all_files.extend(files)
            else:
                logger.warning(f"No files returned for page {page}, stopping pagination")
                break

        self.stats["fetched"] = len(all_files)
        logger.success(f"✓ Total fetched: {len(all_files)} files from {page} page(s)")
        return all_files

    async def download_and_encode_audio(self,
                                       client: httpx.AsyncClient,
                                       file_info: Dict,
                                       index: int) -> Optional[Dict]:
        """Download audio file and convert to base64 string"""
        try:
            # Extract file information using actual API fields
            file_name = file_info.get("name", f"audio_{index}")
            relative_url = file_info.get("relativeUrl", "")
            file_info_data = file_info.get("fileInfo", {})

            # Debug: Show full file_info structure for first file
            if index == 0:
                logger.info(f"File info keys: {list(file_info.keys())}")
                logger.info(f"Full file_info: {json.dumps(file_info, indent=2)[:1000]}")
                logger.info(f"FileInfo data: {json.dumps(file_info_data, indent=2)[:500]}")

            # Check if there's a downloadUrl or signedUrl in fileInfo
            download_url = None
            if isinstance(file_info_data, dict):
                download_url = (file_info_data.get("downloadUrl") or
                              file_info_data.get("signedUrl") or
                              file_info_data.get("url") or
                              file_info_data.get("fileUrl"))

            # If no download URL in fileInfo, construct from relative URL
            if not download_url and relative_url:
                # Remove leading slash if present
                relative_url = relative_url.lstrip("/")
                download_url = f"https://aikosha-api.indiaai.gov.in/{relative_url}"

            audio_url = download_url

            # Debug first URL
            if index == 0:
                logger.info(f"Constructed download URL: {audio_url}")

            # Extract text/transcript from fileInfo
            text = ""
            if isinstance(file_info_data, dict):
                text = (file_info_data.get("text") or
                       file_info_data.get("transcription") or
                       file_info_data.get("transcript") or
                       file_info_data.get("label") or
                       file_info_data.get("annotation") or
                       "")

            if not audio_url:
                logger.error(f"✗ No URL found for file {index + 1}: {file_name}")
                logger.error(f"Available fields: {list(file_info.keys())}")
                self.stats["failed"] += 1
                return None

            logger.info(f"Downloading {index + 1}/{self.stats['fetched']}: {file_name}")

            # Download the audio file with authentication headers
            response = await client.get(
                audio_url,
                headers=self.get_headers(),
                timeout=REQUEST_TIMEOUT,
                follow_redirects=True
            )

            if response.status_code == 200:
                # Convert audio bytes to base64 string
                audio_bytes = response.content
                audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

                self.stats["downloaded"] += 1
                self.stats["encoded"] += 1

                logger.success(f"✓ Downloaded & encoded {index + 1}: {file_name} ({len(audio_bytes)} bytes)")

                return {
                    "audio_to_string": audio_base64,
                    "txt": text
                }
            else:
                self.stats["failed"] += 1
                error_msg = response.text[:200] if response.text else "No error message"
                logger.error(f"✗ Download failed {index + 1}: {response.status_code} - {error_msg}")
                return None

        except Exception as e:
            self.stats["failed"] += 1
            logger.error(f"✗ Exception processing {index + 1}: {str(e)}")
            return None

    async def process_all_files(self, file_list: List[Dict], target_count: int = 50) -> List[Dict]:
        """Download and encode audio files until we get target_count successful samples"""
        logger.info(f"\n{'='*70}")
        logger.info(f"Processing {len(file_list)} audio files (target: {target_count} successful)")
        logger.info(f"Max concurrent downloads: {MAX_CONCURRENT}")
        logger.info(f"{'='*70}\n")

        semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        valid_results = []

        async def process_limited(file_info, index):
            async with semaphore:
                async with httpx.AsyncClient() as client:
                    return await self.download_and_encode_audio(client, file_info, index)

        # Process files until we get enough successful downloads
        for i, file_info in enumerate(file_list):
            if len(valid_results) >= target_count:
                logger.info(f"\n✓ Reached target of {target_count} successful downloads. Stopping.\n")
                break

            result = await process_limited(file_info, i)
            if result:
                valid_results.append(result)
                logger.info(f"Progress: {len(valid_results)}/{target_count} successful downloads")

        logger.info(f"\n✓ Successfully processed: {len(valid_results)}/{target_count} target\n")
        return valid_results

    def save_to_json(self, samples: List[Dict], output_file: Path):
        """Save audio samples to JSON file"""
        logger.info(f"Saving {len(samples)} samples to {output_file}...")

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(samples, f, indent=2, ensure_ascii=False)

        logger.success(f"✓ Saved to {output_file}\n")


async def main():
    """Main execution"""
    parser = argparse.ArgumentParser(description="Download audio samples from Aikosha API")
    parser.add_argument("--target", type=int, default=50, help="Target number of successful downloads (default: 50)")
    parser.add_argument("--fetch-limit", type=int, default=10, help="Number of files to fetch per page (default: 10)")
    parser.add_argument("--pages", type=int, default=10, help="Number of pages to fetch (default: 10)")
    parser.add_argument("--api-key", type=str, default=None, help="Aikosha API key")
    parser.add_argument("--output", type=str, default=None, help="Output JSON file path")

    args = parser.parse_args()

    # Get API key
    api_key = args.api_key or os.getenv("AIKOSHA_API_KEY")
    if not api_key:
        logger.error("✗ API key not provided. Use --api-key or set AIKOSHA_API_KEY in .env")
        sys.exit(1)

    # Set output file
    output_file = Path(args.output) if args.output else OUTPUT_FILE

    logger.info(f"\n{'='*70}")
    logger.info(f"Audio Sample Downloader - Aikosha API")
    logger.info(f"API: {API_BASE_URL}")
    logger.info(f"Dataset: {DATASET_IDENTIFIER}")
    logger.info(f"Files per page: {args.fetch_limit}")
    logger.info(f"Pages to fetch: {args.pages}")
    logger.info(f"Target successful downloads: {args.target}")
    logger.info(f"Output: {output_file}")
    logger.info(f"{'='*70}\n")

    downloader = AudioSampleDownloader(api_key)

    # Step 1: Fetch file list from API (multiple pages)
    async with httpx.AsyncClient() as client:
        file_list = await downloader.fetch_multiple_pages(client, args.fetch_limit, args.pages)

    if not file_list:
        logger.error("✗ No files fetched. Exiting.")
        sys.exit(1)

    # Step 2: Download and encode audio files until we get target count
    samples = await downloader.process_all_files(file_list, args.target)

    if not samples:
        logger.error("✗ No samples processed. Exiting.")
        sys.exit(1)

    # Step 3: Save to JSON
    downloader.save_to_json(samples, output_file)

    # Summary
    logger.info(f"\n{'='*70}")
    logger.info(f"SUMMARY")
    logger.info(f"{'='*70}")
    logger.info(f"Files fetched: {downloader.stats['fetched']}")
    logger.info(f"Successfully downloaded: {downloader.stats['downloaded']}")
    logger.info(f"Successfully encoded: {downloader.stats['encoded']}")
    logger.info(f"Failed: {downloader.stats['failed']}")
    logger.info(f"Output file: {output_file}")
    logger.info(f"{'='*70}\n")


if __name__ == "__main__":
    asyncio.run(main())
