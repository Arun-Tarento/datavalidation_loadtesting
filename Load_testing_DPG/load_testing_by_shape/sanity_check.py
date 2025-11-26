#!/usr/bin/env python3
"""
Sanity check script for all load shape test configurations
Verifies that all configs load correctly and samples are accessible
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

def check_config(config_name, config_class):
    """Check if a config loads successfully and has samples"""
    print(f"\n{'='*70}")
    print(f"Checking {config_name}...")
    print('='*70)

    try:
        config = config_class()
        print(f"✅ {config_name} initialized successfully")

        # Check service_id
        if hasattr(config, 'service_id'):
            print(f"   Service ID: {config.service_id}")

        # Check samples based on service type
        samples_attr = None
        if hasattr(config, 'asr_samples'):
            samples_attr = 'asr_samples'
        elif hasattr(config, 'nmt_samples'):
            samples_attr = 'nmt_samples'
        elif hasattr(config, 'tts_samples'):
            samples_attr = 'tts_samples'
        elif hasattr(config, 'ner_samples'):
            samples_attr = 'ner_samples'
        elif hasattr(config, 'ocr_samples'):
            samples_attr = 'ocr_samples'
        elif hasattr(config, 'transliteration_samples'):
            samples_attr = 'transliteration_samples'
        elif hasattr(config, 'tld_samples'):
            samples_attr = 'tld_samples'
        elif hasattr(config, 'speaker_diarization_samples'):
            samples_attr = 'speaker_diarization_samples'
        elif hasattr(config, 'language_diarization_samples'):
            samples_attr = 'language_diarization_samples'
        elif hasattr(config, 'ald_samples'):
            samples_attr = 'ald_samples'

        if samples_attr:
            samples = getattr(config, samples_attr)
            print(f"   Samples loaded: {len(samples)} items")
            if len(samples) > 0:
                print(f"   ✅ First sample preview: {str(samples[0])[:100]}...")
            else:
                print(f"   ❌ ERROR: No samples loaded!")
                return False
        else:
            print(f"   ⚠️  WARNING: Could not find samples attribute")

        # Check language configs if applicable
        if hasattr(config, 'source_language'):
            print(f"   Source Language: {config.source_language}")
        if hasattr(config, 'target_language'):
            print(f"   Target Language: {config.target_language}")

        # Check auth
        if hasattr(config, 'auth_token'):
            token_preview = config.auth_token[:20] + "..." if len(config.auth_token) > 20 else config.auth_token
            print(f"   Auth Token: {token_preview}")

        print(f"✅ {config_name} passed all checks")
        return True

    except Exception as e:
        print(f"❌ ERROR in {config_name}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run sanity checks on all configs"""
    print("\n" + "="*70)
    print("LOAD SHAPE TEST CONFIGURATIONS - SANITY CHECK")
    print("="*70)

    results = {}

    # Import all config classes
    try:
        from shape_config import (
            ASRConfig, NMTConfig, TTSConfig, NERConfig,
            OCRConfig, TransliterationConfig, TLDConfig,
            SpeakerDiarizationConfig, LanguageDiarizationConfig,
            AudioLanguageDetectionConfig
        )
        print("✅ All config classes imported successfully")
    except Exception as e:
        print(f"❌ ERROR importing config classes: {e}")
        return 1

    # Check each config
    configs = [
        ("ASRConfig", ASRConfig),
        ("NMTConfig", NMTConfig),
        ("TTSConfig", TTSConfig),
        ("NERConfig", NERConfig),
        ("OCRConfig", OCRConfig),
        ("TransliterationConfig", TransliterationConfig),
        ("TLDConfig", TLDConfig),
        ("SpeakerDiarizationConfig", SpeakerDiarizationConfig),
        ("LanguageDiarizationConfig", LanguageDiarizationConfig),
        ("AudioLanguageDetectionConfig", AudioLanguageDetectionConfig),
    ]

    for config_name, config_class in configs:
        results[config_name] = check_config(config_name, config_class)

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for config_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {config_name}")

    print("\n" + "="*70)
    print(f"Results: {passed}/{total} configs passed")
    print("="*70)

    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
