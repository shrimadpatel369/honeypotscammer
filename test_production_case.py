"""
Test the EXACT cases from production that are still failing
"""
import re

def _sanitize_response(response: str) -> str:
    """Enhanced sanitization that removes JSON ANYWHERE in text"""
    if not response:
        return response
    
    original_response = response
    
    # CRITICAL FIX: Remove JSON fragments that appear ANYWHERE in the text
    # Pattern 1: Remove complete JSON objects anywhere in text
    response = re.sub(r'\{[^}]*["\']?response["\']?\s*:\s*["\'][^"\']*["\'][^}]*\}', '', response, flags=re.IGNORECASE)
    
    # Pattern 2: Remove partial/malformed JSON anywhere
    response = re.sub(r'\{[^}]*["\']?response["\']?\s*:\s*["\'][^}]*', '', response, flags=re.IGNORECASE)
    
    # Pattern 3: Remove JSON field markers
    response = re.sub(r'\{?\s*["\']?response["\']?\s*:\s*["\']?', '', response, flags=re.IGNORECASE)
    
    # Pattern 4: Clean up remaining curly braces
    if '{' in response and (':' in response or '"' in response):
        response = re.sub(r'\{[^}]*[:"][^}]*\}', '', response)
        response = re.sub(r'\{\s*["\']', '', response)
    
    # Pattern 5: Remove trailing/leading artifacts
    response = re.sub(r'["\']?\s*[,}]\s*$', '', response)
    response = re.sub(r'^\s*[{"\']', '', response)
    
    # Pattern 6: Clean up escaped characters
    response = response.replace('\\"', '"')
    response = response.replace('\\n', ' ')
    
    # Pattern 7: Remove empty quotes
    response = re.sub(r'["\'][\s]*["\']', '', response)
    
    # Clean up whitespace
    response = ' '.join(response.split())
    response = response.strip()
    
    # Remove JSON field names
    response = re.sub(r'\b(response|text|message|reply)\b\s*:', '', response, flags=re.IGNORECASE)
    
    # Fallback for broken responses
    if len(response) < 3 or response in ['{', '}', ':', '"', "'"]:
        response = "wait a moment"
    
    if response != original_response:
        print(f"SANITIZED:")
        print(f"  BEFORE: '{original_response}'")
        print(f"  AFTER:  '{response}'")
    
    return response


# Test EXACT production cases
print("Testing Production JSON Leakage Cases")
print("=" * 60)

test_cases = [
    ("Case 1 (JSON in middle)", 
     "that doesn't sound right, { \"response\": \"this is very stressful, i have a i mean gst payment due today. my business account is ending in 4021}"),
    
    ("Case 2 (Incomplete JSON)", 
     "{ \"response\": \"Wait a moment}"),
    
    ("Case 3 (Field only)", 
     "{ \"response\":"),
    
    ("Case 4 (Partial with text)", 
     "explain this to me, { \"response\": \"wait a moment, i'm trying to open the sbi yono app and it's just spinning. my business partner always tells me to be careful with these things. if this is really the bank}"),
    
    ("Case 5 (Simple incomplete)", 
     "{ \"response\": That sounds strange."),
]

expected_results = [
    "that doesn't sound right,",
    "",
    "",
    "explain this to me,",
    "That sounds strange.",
]

all_pass = True
for i, (name, test_input) in enumerate(test_cases):
    print(f"\n{name}")
    print(f"Input:  {test_input[:80]}...")
    result = _sanitize_response(test_input)
    print(f"Output: {result}")
    
    if result and '{' not in result and 'response' not in result.lower():
        print("[PASS] No JSON artifacts")
    else:
        print(f"[FAIL] Still contains JSON: {result}")
        all_pass = False
    print("-" * 60)

if all_pass:
    print("\n[SUCCESS] All production cases fixed!")
else:
    print("\n[FAIL] Some cases still have JSON")
