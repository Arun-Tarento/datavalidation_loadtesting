#!/usr/bin/env python3
"""
Helper script to encode images to base64 and update ocr_samples.json

Usage:
    python3 encode_images_for_ocr.py path/to/hindi_image.png path/to/tamil_image.png
"""

import sys
import os
import json
import base64

def encode_image_to_base64(image_path):
    """Encode an image file to base64 string"""
    try:
        with open(image_path, 'rb') as image_file:
            encoded = base64.b64encode(image_file.read()).decode('utf-8')
            return encoded
    except Exception as e:
        print(f"Error encoding {image_path}: {e}")
        return None

def update_ocr_samples(hindi_image_path=None, tamil_image_path=None):
    """Update ocr_samples.json with base64 encoded images"""

    # Get paths to files
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "ocr/ocr_samples.json")

    # Read current JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    samples = data.get("ocr_samples", [])

    # Encode and update Hindi sample
    if hindi_image_path and os.path.exists(hindi_image_path):
        print(f"Encoding Hindi image: {hindi_image_path}")
        hindi_b64 = encode_image_to_base64(hindi_image_path)
        if hindi_b64:
            for sample in samples:
                if sample.get("language") == "hi":
                    sample["imageContent"] = hindi_b64
                    print(f"✓ Updated Hindi sample (size: {len(hindi_b64)} chars)")
                    break
    else:
        print(f"Hindi image not found or not provided: {hindi_image_path}")

    # Encode and update Tamil sample
    if tamil_image_path and os.path.exists(tamil_image_path):
        print(f"Encoding Tamil image: {tamil_image_path}")
        tamil_b64 = encode_image_to_base64(tamil_image_path)
        if tamil_b64:
            for sample in samples:
                if sample.get("language") == "ta":
                    sample["imageContent"] = tamil_b64
                    print(f"✓ Updated Tamil sample (size: {len(tamil_b64)} chars)")
                    break
    else:
        print(f"Tamil image not found or not provided: {tamil_image_path}")

    # Write updated JSON
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Successfully updated {json_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nExample:")
        print("  python3 encode_images_for_ocr.py hindi.png tamil.png")
        print("  python3 encode_images_for_ocr.py hindi.png  # Only update Hindi")
        print("\nCurrent directory:", os.getcwd())
        sys.exit(1)

    hindi_path = sys.argv[1] if len(sys.argv) > 1 else None
    tamil_path = sys.argv[2] if len(sys.argv) > 2 else None

    update_ocr_samples(hindi_path, tamil_path)
