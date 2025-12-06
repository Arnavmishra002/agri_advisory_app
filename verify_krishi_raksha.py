
import os
import django
import sys
import json

# Setup Django Environment
sys.path.append('c:\\AI\\agri_advisory_app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agri_advisory_app.settings')
django.setup()

from advisory.services.krishi_raksha_pest_service import KrishiRakshaPestService

def test_pipeline():
    print("=== Testing KrishiRaksha 2.0 Pipeline ===")
    service = KrishiRakshaPestService()
    
    # Case 1: Tomato (Specialist Logic)
    print("\n[Test 1] Predicting for TOMATO in Delhi (Simulated)")
    result = service.diagnose_crop(
        session_id="test-session-1",
        crop_name="tomato",
        location="Delhi",
        images={}
    )
    
    print(f"Status: {result.get('status')}")
    print(f"Pipeline Stages: {json.dumps(result.get('pipeline_stages'), indent=2)}")
    
    diagnosis = result.get('diagnosis', [])
    print(f"Diagnoses Found: {len(diagnosis)}")
    for d in diagnosis:
        print(f"  - {d['name']} (Conf: {d['confidence']}, Sev: {d.get('severity_label')})")
        if 'verification_note' in d:
             print(f"    Verification Note: {d['verification_note']}")

    # Case 2: Rice (Specialist Logic)
    print("\n[Test 2] Predicting for RICE in Mumbai")
    result_rice = service.diagnose_crop(
        session_id="test-session-2",
        crop_name="rice",
        location="Mumbai",
        images={}
    )
    print(f"Status: {result_rice.get('status')}")
    print(f"Top Detection: {result_rice.get('diagnosis', [{}])[0].get('name')}")

    # Case 3: Unknown Crop (Generalist Logic)
    print("\n[Test 3] Predicting for UNKNOWN CROP")
    result_general = service.diagnose_crop(
        session_id="test-session-3",
        crop_name="unknown",
        location="Delhi",
        images={}
    )
    print(f"Detected Crop: {result_general.get('crop_detected')}")
    print(f"Diagnosis: {result_general.get('diagnosis', [{}])[0].get('name')}")

if __name__ == "__main__":
    test_pipeline()
