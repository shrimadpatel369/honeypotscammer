"""
Test script for Hinglish and Gujarati-English transliterated language support
Demonstrates scam detection and AI responses in transliterated Indian languages
"""

import asyncio
import sys
import os

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ai_agent import AIAgentService
from app.services.scam_detector import ScamDetectorService


# Test cases for Hinglish (Hindi written in English)
HINGLISH_TEST_CASES = [
    {
        "message": "Aapka account block hone wala hai. Abhi OTP share karo.",
        "expected_scam": True,
        "description": "Bank account threat + OTP request in Hinglish"
    },
    {
        "message": "Tumhara card expire ho gaya. Link pe click karke update karo.",
        "expected_scam": True,
        "description": "Card expiry + suspicious link in Hinglish"
    },
    {
        "message": "Congratulations! Aapko 25 lakh ka prize mila hai.",
        "expected_scam": True,
        "description": "Prize scam in Hinglish"
    },
    {
        "message": "SBI bank se bol raha hun. Aapka KYC pending hai.",
        "expected_scam": True,
        "description": "Bank impersonation in Hinglish"
    },
    {
        "message": "Bhai mera phone kharab ho gaya, thoda balance bhej do",
        "expected_scam": False,
        "description": "Casual friend request (not urgent scam)"
    }
]

# Test cases for Gujarati-English (Gujarati written in English)
GUJARATI_ENGLISH_TEST_CASES = [
    {
        "message": "Tamaru account block thava walu che. Atyare OTP share karo.",
        "expected_scam": True,
        "description": "Bank account threat + OTP request in Gujarati-English"
    },
    {
        "message": "Tamaro card expire thai gayo. Link par click kari update karo.",
        "expected_scam": True,
        "description": "Card expiry + suspicious link in Gujarati-English"
    },
    {
        "message": "Congratulations! Tamne 25 lakh no prize mali che.",
        "expected_scam": True,
        "description": "Prize scam in Gujarati-English"
    },
    {
        "message": "SBI bank thi bolu chu. Tamaru KYC pending che.",
        "expected_scam": True,
        "description": "Bank impersonation in Gujarati-English"
    },
    {
        "message": "Bhai maro phone kharab thai gayo, thodo balance mokal",
        "expected_scam": False,
        "description": "Casual friend request in Gujarati"
    }
]


async def test_scam_detection(language_name: str, test_cases: list):
    """Test scam detection for transliterated languages"""
    print(f"\n{'='*80}")
    print(f"Testing Scam Detection: {language_name}")
    print(f"{'='*80}\n")
    
    detector = ScamDetectorService()
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['description']}")
        print(f"Message: \"{test['message']}\"")
        
        # Run scam detection
        is_scam, confidence, indicators = await detector.detect_scam(
            current_message=test['message'],
            conversation_history=[],
            metadata={
                'channel': 'SMS',
                'language': language_name.lower().replace(' ', '_').replace('-', '_'),
                'locale': 'IN'
            }
        )
        
        # Check result
        expected = test['expected_scam']
        result = "✅ PASS" if is_scam == expected else "❌ FAIL"
        
        if is_scam == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"Expected Scam: {expected} | Detected: {is_scam} | Confidence: {confidence:.2f}")
        print(f"Indicators: {indicators}")
        print(f"{result}")
    
    print(f"\n{'-'*80}")
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print(f"Success Rate: {(passed/len(test_cases)*100):.1f}%")
    print(f"{'-'*80}\n")
    
    return passed, failed


async def test_ai_responses(language_name: str, test_messages: list):
    """Test AI response generation in transliterated languages"""
    print(f"\n{'='*80}")
    print(f"Testing AI Responses: {language_name}")
    print(f"{'='*80}\n")
    
    agent = AIAgentService()
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n--- Conversation {i} ---")
        print(f"Scammer: {message}")
        
        # Generate AI response
        try:
            response, should_continue = await agent.generate_response(
                current_message=message,
                conversation_history=[
                    {"sender": "scammer", "text": message, "timestamp": "2026-02-16T10:00:00"}
                ],
                session_context={
                    "sessionId": f"test_{language_name}_{i}",
                    "scamType": "banking"
                },
                metadata={
                    'channel': 'SMS',
                    'language': language_name.lower().replace(' ', '_').replace('-', '_'),
                    'locale': 'IN'
                }
            )
            
            print(f"AI (Victim): {response}")
            print(f"Continue conversation: {should_continue}")
            
        except Exception as e:
            print(f"❌ Error generating response: {e}")
    
    print(f"\n{'-'*80}\n")


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("HINGLISH & GUJARATI-ENGLISH LANGUAGE SUPPORT TEST")
    print("="*80)
    
    # Test Hinglish scam detection
    hinglish_passed, hinglish_failed = await test_scam_detection(
        "Hinglish (Hindi-English)", 
        HINGLISH_TEST_CASES
    )
    
    # Test Gujarati-English scam detection
    gujarati_passed, gujarati_failed = await test_scam_detection(
        "Gujarati-English", 
        GUJARATI_ENGLISH_TEST_CASES
    )
    
    # Test Hinglish AI responses
    await test_ai_responses(
        "Hinglish",
        [
            "Aapka account block hone wala hai. OTP bhejo",
            "Urgent! Bank se bol raha hun. Account verify karo",
            "Aapko lottery me 50 lakh jeet hai. Details bhejo"
        ]
    )
    
    # Test Gujarati-English AI responses
    await test_ai_responses(
        "Gujarati-English",
        [
            "Tamaru account block thava walu che. OTP mokalo",
            "Urgent! Bank thi bolu chu. Account verify karo",
            "Tamne lottery ma 50 lakh jeeti che. Details mokalo"
        ]
    )
    
    # Overall summary
    print("\n" + "="*80)
    print("OVERALL TEST SUMMARY")
    print("="*80)
    total_tests = len(HINGLISH_TEST_CASES) + len(GUJARATI_ENGLISH_TEST_CASES)
    total_passed = hinglish_passed + gujarati_passed
    total_failed = hinglish_failed + gujarati_failed
    
    print(f"\nTotal Tests: {total_tests}")
    print(f"Passed: {total_passed} ({total_passed/total_tests*100:.1f}%)")
    print(f"Failed: {total_failed} ({total_failed/total_tests*100:.1f}%)")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
