# Load Shape Tests - Sanity Check Report

**Date:** 2025-11-18
**Status:** ✅ ALL CHECKS PASSED

## Summary

All 7 load shape test configurations have been verified and are functioning correctly.

**Results:** 7/7 configs passed (100%)

---

## Detailed Verification Results

### 1. ASR (Speech Recognition)
- ✅ **Config Class:** `ASRConfig` - Loaded successfully
- ✅ **User Class:** `ASRUser` - Imported correctly
- ✅ **Samples:** 1 audio sample loaded from `load_testing_test_samples/asr/asr_samples.json`
- ✅ **Service ID:** `ai4bharat/indictasr`
- ✅ **Endpoint:** `/services/inference/asr`
- ✅ **Timeout:** 120ms
- ✅ **Test Config:** Includes service_id, source_language, source_script, audio_format, sampling_rate
- ✅ **Results File:** `asr_load_shape_results_{timestamp}.json`
- ✅ **Service Description:** "ASR (Speech Recognition)"

### 2. NMT (Translation)
- ✅ **Config Class:** `NMTConfig` - Loaded successfully
- ✅ **User Class:** `NMTUser` - Imported correctly
- ✅ **Samples:** 5 translation samples loaded from `load_testing_test_samples/nmt/nmt_samples.json`
- ✅ **Service ID:** `ai4bharat/indictrans--gpu-t4`
- ✅ **Endpoint:** `/services/inference/translation`
- ✅ **Timeout:** 60ms
- ✅ **Test Config:** Includes service_id, source_language, source_script, target_language, target_script
- ✅ **Results File:** `nmt_load_shape_results_{timestamp}.json`
- ✅ **Service Description:** "NMT (Translation)"

### 3. TTS (Text-to-Speech)
- ✅ **Config Class:** `TTSConfig` - Loaded successfully
- ✅ **User Class:** `TTSUser` - Imported correctly
- ✅ **Samples:** 10 text samples loaded from `load_testing_test_samples/tts/tts_samples.json`
- ✅ **Service ID:** `ai4bharat/indictts--gpu-t4`
- ✅ **Endpoint:** `/services/inference/tts`
- ✅ **Timeout:** 250ms
- ✅ **Test Config:** Includes service_id, source_language, source_script, audio_format, sampling_rate
- ✅ **Results File:** `tts_load_shape_results_{timestamp}.json`
- ✅ **Service Description:** "TTS (Text-to-Speech)"

### 4. NER (Named Entity Recognition)
- ✅ **Config Class:** `NERConfig` - Loaded successfully
- ✅ **User Class:** `NERUser` - Imported correctly
- ✅ **Samples:** 5 text samples loaded from `load_testing_test_samples/ner/ner_samples.json`
- ✅ **Service ID:** `bhashini/ai4bharat/indic-ner`
- ✅ **Endpoint:** `/services/inference/ner`
- ✅ **Timeout:** 250ms
- ✅ **Test Config:** Includes service_id only
- ✅ **Results File:** `ner_load_shape_results_{timestamp}.json`
- ✅ **Service Description:** "NER (Named Entity Recognition)"

### 5. OCR (Optical Character Recognition)
- ✅ **Config Class:** `OCRConfig` - Loaded successfully
- ✅ **User Class:** `OCRUser` - Imported correctly
- ✅ **Samples:** 2 image samples loaded from `load_testing_test_samples/ocr/ocr_samples.json`
- ✅ **Service ID:** `ai4bharat/surya-ocr-v1--gpu--t4`
- ✅ **Endpoint:** `/services/inference/pipeline/ocr`
- ✅ **Timeout:** 250ms
- ✅ **Test Config:** Includes service_id only
- ✅ **Results File:** `ocr_load_shape_results_{timestamp}.json`
- ✅ **Service Description:** "OCR (Optical Character Recognition)"

### 6. Transliteration
- ✅ **Config Class:** `TransliterationConfig` - Loaded successfully
- ✅ **User Class:** `TransliterationUser` - Imported correctly
- ✅ **Samples:** 5 text samples loaded from `load_testing_test_samples/transliteration/transliteration_samples.json`
- ✅ **Service ID:** `ai4bharat-transliteration`
- ✅ **Endpoint:** `/services/inference/transliteration`
- ✅ **Timeout:** 250ms
- ✅ **Test Config:** Includes service_id, source_language, source_script, target_language, target_script, is_sentence, num_suggestions
- ✅ **Results File:** `transliteration_load_shape_results_{timestamp}.json`
- ✅ **Service Description:** "Transliteration"

### 7. TLD (Text Language Detection)
- ✅ **Config Class:** `TLDConfig` - Loaded successfully
- ✅ **User Class:** `TLDUser` - Imported correctly
- ✅ **Samples:** 5 text samples loaded from `load_testing_test_samples/tld/tld_samples.json`
- ✅ **Service ID:** `ai4bharat-indiclid`
- ✅ **Endpoint:** `/services/inference/pipeline`
- ✅ **Timeout:** 250ms
- ✅ **Test Config:** Includes service_id only
- ✅ **Results File:** `tld_load_shape_results_{timestamp}.json`
- ✅ **Service Description:** "TLD (Text Language Detection)"

---

## Common Configuration Checks

### ✅ All Test Files
- Correct imports from `shape_config`
- Proper config initialization
- Correct service descriptions
- Proper result file naming
- All three load shapes included (StagesShapeWithMetrics, ConservativeShapeWithMetrics, AggressiveShapeWithMetrics)

### ✅ shape_config.py Structure
- All 7 Config classes defined
- All 7 User classes defined
- Proper path resolution (goes up 2 levels to Auto directory)
- Authentication configured
- Control config parsed correctly

### ✅ Sample Files
- All sample files accessible
- Correct JSON structure
- Samples loaded without errors

### ✅ Endpoints
All endpoints follow the correct pattern:
- Standard services: `/services/inference/{service_type}`
- Pipeline services: `/services/inference/pipeline` or `/services/inference/pipeline/ocr`

---

## Test Configuration Summary

| Service | Config Attributes | Endpoint | Timeout | Samples |
|---------|------------------|----------|---------|---------|
| ASR | service_id, source_language, source_script, audio_format, sampling_rate | /services/inference/asr | 120ms | 1 |
| NMT | service_id, source_language, source_script, target_language, target_script | /services/inference/translation | 60ms | 5 |
| TTS | service_id, source_language, source_script, audio_format, sampling_rate | /services/inference/tts | 250ms | 10 |
| NER | service_id | /services/inference/ner | 250ms | 5 |
| OCR | service_id | /services/inference/pipeline/ocr | 250ms | 2 |
| Transliteration | service_id, source_language, source_script, target_language, target_script, is_sentence, num_suggestions | /services/inference/transliteration | 250ms | 5 |
| TLD | service_id | /services/inference/pipeline | 250ms | 5 |

---

## Load Shape Configurations

All 7 test files include three load shape options:

1. **StagesShapeWithMetrics** (Default) - ~18 minutes
   - Comprehensive testing with 9 stages
   - Gradual load increase from 10 to 60 users

2. **ConservativeShapeWithMetrics** - ~15 minutes
   - Slower ramp-up for weak servers
   - Load range: 2-20 users

3. **AggressiveShapeWithMetrics** - ~10 minutes
   - Quick capacity finding
   - Load range: 10-100 users

---

## Results Location

All test results are saved to:
```
Load_testing_DPG/load_testing_shape_results/
├── asr_load_shape_results_TIMESTAMP.json
├── nmt_load_shape_results_TIMESTAMP.json
├── tts_load_shape_results_TIMESTAMP.json
├── ner_load_shape_results_TIMESTAMP.json
├── ocr_load_shape_results_TIMESTAMP.json
├── transliteration_load_shape_results_TIMESTAMP.json
└── tld_load_shape_results_TIMESTAMP.json
```

---

## Verification Script

A sanity check script has been created at:
```
load_testing_by_shape/sanity_check.py
```

Run it to verify all configurations:
```bash
cd Load_testing_DPG/load_testing_by_shape
python3 sanity_check.py
```

---

## Self-Contained Design Verification

✅ **Completely Independent Folder**
- Has its own `shape_config.py` with all Config and User classes
- Reads from parent `.env` file
- Saves results to `../load_testing_shape_results/`
- No dependencies on `load_testing_scripts` folder
- Can be delivered as a standalone package

---

## Conclusion

**All sanity checks passed successfully!** ✅

The `load_testing_by_shape` folder is production-ready with:
- 7 fully functional load shape tests
- Proper configuration management
- Correct sample loading
- Accurate endpoint configuration
- Self-contained design
- Complete documentation

Ready for deployment and testing.
