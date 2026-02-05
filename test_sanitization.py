"""
Test script to verify JSON sanitization in AI agent responses
"""
import re

def _sanitize_response(response: str) -> str:
    """
    Sanitize AI response to remove any JSON structure artifacts.
    Ensures only natural language text is returned to scammers.
    """
    if not response:
        return response
    
    original_response = response
    
    # Remove common JSON structure patterns
    # Pattern 1: Full JSON object like { "response": "text" }
    json_object_pattern = r'^\s*\{\s*["\']?response["\']?\s*:\s*["\'](.+?)["\']\s*(?:,.*?)?\}\s*$'
    match = re.match(json_object_pattern, response, re.DOTALL | re.IGNORECASE)
    if match:
        response = match.group(1)
        print(f"[OK] Cleaned full JSON object from response")
    
    # Pattern 2: Partial JSON like { "response": "text or "response": "text"
    partial_json_pattern = r'^\s*\{?\s*["\']?response["\']?\s*:\s*["\'](.+?)$'
    match = re.match(partial_json_pattern, response, re.DOTALL | re.IGNORECASE)
    if match:
        response = match.group(1)
        print(f"[OK] Cleaned partial JSON from response")

    
    # Pattern 3: Remove leading/trailing curly braces that shouldn't be in natural text
    # Only remove if they're wrapping the entire response
    response = response.strip()
    if response.startswith('{') and response.endswith('}') and response.count('{') == 1:
        # Check if it looks like JSON (contains colons and quotes)
        if ':' in response and '"' in response:
            # Try to extract just the text value
            value_pattern = r'["\'](.+?)["\']'
            matches = re.findall(value_pattern, response)
            if matches:
                # Get the longest match (likely the actual response text)
                response = max(matches, key=len)
                print(f"[OK] Extracted text from curly-brace wrapped JSON")
    
    # Pattern 4: Remove JSON field names that might be at the start
    field_pattern = r'^\s*["\']?(?:response|text|message|reply)["\']?\s*:\s*["\']?'
    response = re.sub(field_pattern, '', response, flags=re.IGNORECASE)
    
    # Pattern 5: Clean up escaped quotes and other JSON artifacts
    response = response.replace('\\"', '"')  # Unescape quotes
    response = response.replace('\\n', ' ')  # Replace escaped newlines with spaces
    
    # Pattern 6: Remove trailing JSON artifacts (closing quotes, braces, etc.)
    response = re.sub(r'["\']?\s*[,}]\s*$', '', response)
    
    # Clean up extra whitespace
    response = ' '.join(response.split())
    response = response.strip()
    
    # If we made significant changes, log it
    if response != original_response:
        print(f"[OK] Sanitized: '{original_response[:50]}...' -> '{response[:50]}...'")

    
    return response


# Test cases
test_cases = [
    # Case 1: Full JSON object
    '{ "response": "wait a moment"}',
    
    # Case 2: Partial JSON
    '{ "response": "let me check',
    
    # Case 3: JSON with field name
    '"response": "I will do that"',
    
    # Case 4: Normal text (should pass through)
    "wait a moment",
    
    # Case 5: JSON with extra fields
    '{ "response": "okay I understand", "should_continue": true}',
    
    # Case 6: Escaped quotes
    'wait a \\"moment\\"',
    
    # Case 7: Complex JSON object
    '{"response": "I am checking my account", "emotional_state": "worried"}',
]

print("Testing JSON Sanitization")
print("=" * 60)

for i, test in enumerate(test_cases, 1):
    print(f"\nTest {i}: {test}")
    result = _sanitize_response(test)
    print(f"Result: {result}")
    print("-" * 60)

print("\n[SUCCESS] All tests completed!")

