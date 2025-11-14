"""
Test single NER (Named Entity Recognition) request to debug issues
Can be run from any directory: python3 Load_testing_DPG/ner_single_request_test.py
"""
import os
import json
from dotenv import load_dotenv
import requests

# Load environment - check script directory first, then project root
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)

# Try to find .env file in script directory first, then project root
env_path = os.path.join(script_dir, '.env')
if not os.path.exists(env_path):
    env_path = os.path.join(project_root, '.env')

load_dotenv(env_path)

# Configuration
auth_token = os.getenv("AUTH_TOKEN", "").strip('"')
x_auth_source = os.getenv("X_AUTH_SOURCE", "AUTH_TOKEN")
service_id = os.getenv("NER_SERVICE_ID", "bhashini/ai4bharat/indic-ner")
base_url = os.getenv("BASE_URL", "http://13.204.164.186:8000")

print("="*70)
print("TESTING NER (NAMED ENTITY RECOGNITION) REQUEST")
print("="*70)
print(f"Base URL: {base_url}")
print(f"Service ID: {service_id}")
print(f"Auth token (first 50 chars): {auth_token[:50]}...")

# Load NER sample with robust path resolution
samples_file = "load_testing_test_samples/ner/ner_samples.json"
samples_path = os.path.join(project_root, samples_file)

print(f"\nLoading NER samples from: {samples_path}")
try:
    with open(samples_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        ner_samples = data.get("ner_samples", [])
        print(f"Loaded {len(ner_samples)} NER samples")

        if ner_samples:
            print(f"\n{'='*70}")
            print("Testing all samples:")
            print(f"{'='*70}\n")

            for idx, sample in enumerate(ner_samples, 1):
                source_text = sample.get("source", "")
                language = sample.get("language", "hi")

                print(f"Sample {idx} (Language: {language}):")
                print(f"  Text: {source_text[:80]}...")

                # Payload
                payload = {
                    "input": [
                        {
                            "source": source_text
                        }
                    ],
                    "config": {
                        "language": {
                            "sourceLanguage": language
                        },
                        "serviceId": service_id
                    },
                    "controlConfig": {
                        "dataTracking": True
                    }
                }

                # Headers
                headers = {
                    "accept": "application/json",
                    "x-auth-source": x_auth_source,
                    "Content-Type": "application/json",
                    "Authorization": auth_token
                }

                # Test NER request
                url = f"{base_url}/services/inference/ner"
                params = {"serviceId": service_id}

                try:
                    response = requests.post(url, params=params, json=payload, headers=headers, timeout=60)

                    if response.status_code == 200:
                        try:
                            data = response.json()
                            if "output" in data and len(data['output']) > 0:
                                tagged = data['output'][0].get('tagged', '')
                                print(f"  ✅ SUCCESS!")
                                print(f"  Tagged result: {tagged[:100]}...")
                            else:
                                print(f"  ⚠️  Response missing output")
                        except Exception as e:
                            print(f"  ⚠️  Could not parse response: {e}")
                    else:
                        print(f"  ❌ FAILED! Status: {response.status_code}")
                        print(f"  Response: {response.text[:200]}")
                except Exception as e:
                    print(f"  ❌ EXCEPTION: {e}")

                print()

            print(f"{'='*70}")
            print("Detailed test of first sample:")
            print(f"{'='*70}\n")

            # Test first sample in detail
            first_sample = ner_samples[0]
            source_text = first_sample.get("source", "")
            language = first_sample.get("language", "hi")
        else:
            print("ERROR: No NER samples found!")
            exit(1)
except Exception as e:
    print(f"ERROR loading samples: {e}")
    print(f"Looking for file at: {samples_path}")
    exit(1)

# Payload for detailed test
payload = {
    "input": [
        {
            "source": source_text
        }
    ],
    "config": {
        "language": {
            "sourceLanguage": language
        },
        "serviceId": service_id
    },
    "controlConfig": {
        "dataTracking": True
    }
}

# Headers
headers = {
    "accept": "application/json",
    "x-auth-source": x_auth_source,
    "Content-Type": "application/json",
    "Authorization": auth_token
}

# Test NER request
print("TEST: NER Request")
print("-" * 70)
url = f"{base_url}/services/inference/ner"
params = {"serviceId": service_id}
print(f"Full URL: {url}?serviceId={service_id}")
print(f"Payload size: {len(json.dumps(payload))} bytes")
print(f"Language: {language}")
print(f"Sample text: {source_text[:100]}...")

try:
    print("\nSending request...")
    response = requests.post(url, params=params, json=payload, headers=headers, timeout=60)
    print(f"✓ Request sent successfully")
    print(f"Status Code: {response.status_code}")
    print(f"Response Length: {len(response.text)} bytes")

    if response.status_code == 200:
        print("✅ SUCCESS!")
        try:
            data = response.json()
            print(f"\nFull response JSON:")
            print(json.dumps(data, indent=2, ensure_ascii=False))

            if "output" in data and len(data['output']) > 0:
                output_data = data['output'][0]
                source = output_data.get('source', '')
                tagged = output_data.get('tagged', '')
                # Try different field names for the NER predictions
                tokens = output_data.get('nerPrediction', output_data.get('tokens', []))

                print(f"\nOriginal text: {source}")
                print(f"\nAvailable fields in output: {list(output_data.keys())}")

                if tagged:
                    print(f"\nTagged result (NER output):")
                    print(tagged)

                # Extract and display named entities from tokens
                if tokens:
                    print(f"\n{'='*70}")
                    print("Named Entities Found:")
                    print(f"{'='*70}")

                    entities = []
                    current_entity = None

                    for token_info in tokens:
                        token = token_info.get('token', '')
                        tag = token_info.get('tag', '')

                        # Handle simple tag format (PER, LOC, ORG) instead of BIO format
                        if tag != 'O' and tag:  # Non-outside entity tag
                            if current_entity and current_entity['type'] == tag:
                                # Continue the current entity
                                current_entity['tokens'].append(token)
                                current_entity['text'] = ' '.join(current_entity['tokens'])
                            else:
                                # Start a new entity
                                if current_entity:
                                    entities.append(current_entity)
                                current_entity = {
                                    'text': token,
                                    'type': tag,
                                    'tokens': [token]
                                }
                        else:  # 'O' tag
                            if current_entity:
                                entities.append(current_entity)
                                current_entity = None

                    # Don't forget the last entity
                    if current_entity:
                        entities.append(current_entity)

                    if entities:
                        # Map tag abbreviations to full names
                        tag_names = {
                            'PER': 'Person',
                            'LOC': 'Location',
                            'ORG': 'Organization',
                            'MISC': 'Miscellaneous'
                        }
                        for entity in entities:
                            entity_type = tag_names.get(entity['type'], entity['type'])
                            print(f"  • {entity['text']} [{entity_type}]")
                    else:
                        print("  No named entities found in this text.")
                    print(f"{'='*70}")
        except Exception as e:
            print(f"⚠️  Could not parse response: {e}")
    else:
        print("❌ FAILED!")
        print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"❌ EXCEPTION: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
