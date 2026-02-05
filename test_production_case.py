"""
Test the exact malformed JSON case from production
"""
import re
import sys
import os

# Add the app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def _sanitize_response(response: str) -> str:
    """Enhanced sanitization logic"""
    if not response:
        return response
    
    original_response = response
    
    # Pattern 1: Full or partial JSON object with proper quotes
    json_pattern = r'^\s*\{\s*["\']?response["\']?\s*:\s*["\'](.+?)["\']\s*(?:,.*?)?\}?\s*$'
    match = re.match(json_pattern, response, re.DOTALL | re.IGNORECASE)
    if match:
        response = match.group(1)
        print(f"[OK] Pattern 1 matched")
    
    # Pattern 2: Malformed JSON with missing closing quote before brace
    malformed_json_pattern = r'^\s*\{\s*["\']?response["\']?\s*:\s*["\'](.+?)\}?\s*$'
    if not match:
        match = re.match(malformed_json_pattern, response, re.DOTALL | re.IGNORECASE)
        if match:
            response = match.group(1)
            print(f"[OK] Pattern 2 matched (malformed JSON)")
    
    # Clean up trailing artifacts
    response = re.sub(r'["\']?\s*[,}]\s*$', '', response)
    response = re.sub(r'^\s*["\']', '', response)
    response = ' '.join(response.split()).strip()
    
    if response != original_response:
        print(f"Sanitized: '{original_response}' -> '{response}'")
    
    return response


# Test the EXACT case from production
print("Testing production malformed JSON case:")
print("="*60)

test_case = '{ "response": "wait a moment, um blocked in two hours? that doesn\'t sound right}'
print(f"Input:  {test_case}")
result = _sanitize_response(test_case)
print(f"Output: {result}")
print()

expected = "wait a moment, um blocked in two hours? that doesn't sound right"
if result == expected:
    print("[SUCCESS] Sanitization working correctly!")
else:
    print(f"[FAIL] Expected: '{expected}'")
    print(f"[FAIL] Got:      '{result}'")
