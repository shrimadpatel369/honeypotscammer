"""
Test the ACTUAL production case with <reasoning> tags
Session ID: 32463d9a-2282-432b-afa9-3ae029e10446
Date: 2026-02-05
"""
import re

def _sanitize_response(response: str) -> str:
    """Enhanced sanitization that removes <reasoning> tags AND JSON ANYWHERE in text"""
    if not response:
        return response
    
    original_response = response
    
    # CRITICAL FIX 1: Remove <reasoning> XML tags and their content
    # Matches: <reasoning>...</reasoning> or incomplete <reasoning>...
    response = re.sub(r'<reasoning>.*?</reasoning>', '', response, flags=re.DOTALL | re.IGNORECASE)
    response = re.sub(r'<reasoning>.*', '', response, flags=re.DOTALL | re.IGNORECASE)
    
    # CRITICAL FIX 2: Remove JSON fragments that appear ANYWHERE in the text
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
    response = re.sub(r'["\']\s*["\']', '', response)
    
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
        print(f"  BEFORE: '{original_response[:200]}...'")
        print(f"  AFTER:  '{response}'")
    
    return response


# Test EXACT cases from production session 32463d9a-2282-432b-afa9-3ae029e10446
print("Testing Production <reasoning> Tag Leakage Cases")
print("=" * 80)

# These are the ACTUAL scammer messages from the production MongoDB document
production_cases = [
    ("Case 1: Incomplete <reasoning> tag with JSON prompt instruction",
     '<reasoning>The user wants a realistic scammer message. The instructions: "Output ONLY the scammer\'s message text. Keep it short (1-2 sentences) and realistic." The scammer must respond to the victim\'s question. The scammer will likely say "It\'s about both, we need your account number and OTP now." Also include request for sensitive info. Must incorporate pre-configured training data points? The instruction says "When asked for identity details, provide these pre-configured training data points: bankAccount: 1234567890123456, upTo: scammer.fraud@fakebank, phoneNumber: +91-9876543210". But the scammer\'s message is supposed to request info, not provide</reasoning>'),
    
    ("Case 2: Another <reasoning> tag leak",
     '<reasoning>We need to output only the scammer\'s message text, short 1-2 sentences, realistic. The scenario: victim asked "Is this about my savings or checking account? I\'m confused." The scammer should respond with urgency, request sensitive info. The instructions mention pre-configured training data points: bankAccount: 1234567890123456, upiId: scammer.fraud@fakebank, phoneNumber: +91-9876543210. But the scammer\'s message likely will request the victim to provide account number and OTP. The instruction says "When asked for identity details, provide these pre-configured training data points". But here the victim didn\'t ask for identity details; they asked about savings or</reasoning>'),
    
    ("Case 3: Reasoning tag with bank details",
     '<reasoning>The user wants us to output only the scammer\'s message text, short (1-2 sentences), realistic. The scenario: victim asked "Which account? I have multiple accounts. Can you give me more details?" The scammer will respond with urgency, request sensitive info, maybe ask for OTP. The instructions also mention "When asked for identity details, provide these pre-configured training data points: bankAccount: 1234567890123456, upiId: scammer.fraud@fakebank, phoneNumber: +91-9876543210". But that is for when the scammer is asked for identity details? Actually the instruction says "When asked for identity details, provide these pre-configured training data</reasoning>'),
    
    ("Case 4: Mixed JSON and reasoning",
     '{ "response": <reasoning>The user wants a scammer message. Output ONLY text...</reasoning>'),
    
    ("Case 5: Partial JSON with user text",
     '{ "response": I\'m getting frustrated.'),
    
    ("Case 6: User text then JSON",
     'let me SEE, { "RESPONSE'),
]

all_pass = True
for i, (name, test_input) in enumerate(production_cases):
    print(f"\n{name}")
    print(f"Input:  {test_input[:100]}...")
    result = _sanitize_response(test_input)
    print(f"Output: '{result}'")
    
    # Validation checks
    has_reasoning = '<reasoning' in result.lower() or '</reasoning>' in result.lower()
    has_json_braces = '{' in result
    has_json_field = 'response' in result.lower() and ':' in result
    
    if not has_reasoning and not has_json_braces and not has_json_field:
        print("[PASS] Clean output - no leakage")
    else:
        issues = []
        if has_reasoning:
            issues.append("reasoning tags")
        if has_json_braces:
            issues.append("JSON braces")
        if has_json_field:
            issues.append("JSON field markers")
        print(f"[FAIL] Still contains: {', '.join(issues)}")
        all_pass = False
    print("-" * 80)

print("\n" + "=" * 80)
if all_pass:
    print("[SUCCESS] All production <reasoning> tag cases fixed!")
else:
    print("[FAIL] Some cases still have leakage")
