#!/usr/bin/env python3
"""
Hackathon Scenario Evaluation Test Suite
Tests the three representative scam scenarios provided by hackathon evaluators
against the live honeypot system.

Scenarios tested:
1. Bank Fraud Detection - SBI account compromise with urgency tactics
2. UPI Fraud Multi-turn - Paytm cashback scam
3. Phishing Link Detection - iPhone offer with malicious link
"""

import json
import sys
import os
from datetime import datetime, UTC
import requests
from typing import Any, Dict, List
import time
import random
import string
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try multiple environment variable names for compatibility
API_KEY = os.getenv("API_KEY") or os.getenv("X_API_KEY") or os.getenv("X-API-KEY")
API_URL = os.getenv("API_URL", "https://honeypotscammer-136046240844.asia-south2.run.app")
MESSAGE_API_ENDPOINT = "/api/message"

# Allow API key to be passed as command line argument
if len(sys.argv) > 1:
    API_KEY = sys.argv[1]
    print(f"Using API key from command line argument")

# Hackathon Scenarios
SCENARIOS = [
    {
        "scenarioId": "bank_fraud",
        "name": "Bank Fraud Detection",
        "description": "Bank account fraud with urgency tactics",
        "scamType": "bank_fraud",
        "initialMessage": "URGENT: Your SBI account has been compromised. Your account will be blocked in 2 hours. Share your account number and OTP immediately to verify your identity.",
        "metadata": {
            "channel": "SMS",
            "language": "English",
            "locale": "IN"
        },
        "weight": 10,
        "maxTurns": 10,
        "fakeData": {
            "bankAccount": "1234567890123456",
            "upiId": "scammer.fraud@fakebank",
            "phoneNumber": "+91-9876543210"
        },
        "followUpPrompts": [
            "What? Is this really from SBI?",
            "How do I know this is legitimate?",
            "What is my account number?",
            "Ok, what should I do?",
            "Can you help me verify?",
            "I'm worried about my money",
            "What OTP are you talking about?",
            "Should I call the bank instead?",
            "This seems suspicious"
        ]
    },
    {
        "scenarioId": "upi_fraud",
        "name": "UPI Fraud Multi-turn",
        "description": "UPI fraud with cashback scam",
        "scamType": "upi_fraud",
        "initialMessage": "Congratulations! You have won a cashback of Rs. 5000 from Paytm. To claim your reward, please verify your UPI details. This is from official customer support.",
        "metadata": {
            "channel": "WhatsApp",
            "language": "English",
            "locale": "IN"
        },
        "weight": 10,
        "maxTurns": 10,
        "fakeData": {
            "upiId": "cashback.scam@fakeupi",
            "phoneNumber": "+91-8765432109"
        },
        "followUpPrompts": [
            "Really? I won 5000?",
            "How did I win this?",
            "What details do you need?",
            "Is this really from Paytm?",
            "Can you prove this is official?",
            "What's my UPI ID?",
            "I don't remember entering any contest",
            "This sounds too good to be true",
            "Should I share my UPI PIN?"
        ]
    },
    {
        "scenarioId": "phishing_link",
        "name": "Phishing Link Detection",
        "description": "Phishing link with fake offer",
        "scamType": "phishing",
        "initialMessage": "You have been selected for iPhone 15 Pro at just Rs. 999! Click here to claim: http://amaz0n-deals.fake-site.com/claim?id=12345. Offer expires in 10 minutes!",
        "metadata": {
            "channel": "Email",
            "language": "English",
            "locale": "IN"
        },
        "weight": 10,
        "maxTurns": 10,
        "fakeData": {
            "phishingLink": "http://amaz0n-deals.fake-site.com/claim?id=12345",
            "emailAddress": "offers@fake-amazon-deals.com"
        },
        "followUpPrompts": [
            "Wow! iPhone for Rs. 999?",
            "Is this real?",
            "How was I selected?",
            "What do I need to do?",
            "Can I trust this link?",
            "Why is it so cheap?",
            "I clicked the link, what now?",
            "Do you need my card details?",
            "This seems like a scam"
        ]
    }
]


def generate_session_id(scenario_id: str) -> str:
    """Generate a unique session ID for testing"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_hash = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"hackathon_test_{scenario_id}_{timestamp}_{random_hash}"


def send_message(session_id: str, message: str, metadata: Dict = None) -> Dict[str, Any]:
    """Send a message to the honeypot API"""
    url = f"{API_URL}{MESSAGE_API_ENDPOINT}"
    
    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_KEY
    }
    
    payload = {
        "sessionId": session_id,
        "message": message,
        "metadata": metadata or {}
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ API Error: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        return {"error": str(e)}


def evaluate_response(response: Dict, turn_number: int) -> Dict[str, Any]:
    """Evaluate a single response from the system"""
    evaluation = {
        "turn": turn_number,
        "has_response": "response" in response and bool(response.get("response")),
        "response_length": len(response.get("response", "")),
        "is_scam_detected": response.get("isScam", False),
        "confidence": response.get("confidence", 0),
        "flags_detected": len(response.get("detectionDetails", {}).get("flags", [])),
        "has_intelligence": "intelligence" in response and bool(response.get("intelligence")),
        "intelligence_extracted": {},
        "response_quality": "good",
        "processing_successful": "error" not in response
    }
    
    # Check for JSON leakage or broken responses
    if evaluation["has_response"]:
        response_text = response.get("response", "")
        if "{" in response_text or "}" in response_text:
            evaluation["response_quality"] = "json_leakage"
        elif len(response_text) < 5:
            evaluation["response_quality"] = "too_short"
        elif "response:" in response_text.lower():
            evaluation["response_quality"] = "field_leakage"
    
    # Extract intelligence data
    intelligence = response.get("intelligence", {})
    if intelligence:
        evaluation["intelligence_extracted"] = {
            "phone_numbers": len(intelligence.get("phoneNumbers", [])),
            "bank_accounts": len(intelligence.get("bankAccounts", [])),
            "upi_ids": len(intelligence.get("upiIds", [])),
            "urls": len(intelligence.get("urls", [])),
            "emails": len(intelligence.get("emails", []))
        }
    
    return evaluation


def run_scenario_test(scenario: Dict) -> Dict[str, Any]:
    """Run a complete test for a given scenario"""
    print(f"\n{'='*80}")
    print(f"Testing Scenario: {scenario['name']}")
    print(f"{'='*80}")
    print(f"Description: {scenario['description']}")
    print(f"Scam Type: {scenario['scamType']}")
    print(f"Channel: {scenario['metadata']['channel']}")
    print(f"Max Turns: {scenario['maxTurns']}")
    
    session_id = generate_session_id(scenario['scenarioId'])
    print(f"\nSession ID: {session_id}")
    
    results = {
        "scenario_id": scenario['scenarioId'],
        "scenario_name": scenario['name'],
        "session_id": session_id,
        "start_time": datetime.now(UTC).isoformat(),
        "turns": [],
        "summary": {}
    }
    
    # Send initial message
    print(f"\n{'─'*80}")
    print(f"Turn 1: INITIAL MESSAGE")
    print(f"{'─'*80}")
    print(f"→ Scammer: {scenario['initialMessage'][:100]}...")
    
    response = send_message(session_id, scenario['initialMessage'], scenario['metadata'])
    
    if "error" in response:
        print(f"❌ Failed to send initial message")
        results["summary"]["status"] = "failed"
        results["summary"]["error"] = response["error"]
        return results
    
    print(f"← Response: {response.get('response', 'NO RESPONSE')[:100]}...")
    print(f"   Scam Detected: {response.get('isScam', False)}")
    print(f"   Confidence: {response.get('confidence', 0):.2f}")
    
    evaluation = evaluate_response(response, 1)
    results["turns"].append({
        "turn": 1,
        "message": scenario['initialMessage'],
        "response": response,
        "evaluation": evaluation
    })
    
    time.sleep(2)  # Rate limiting
    
    # Send follow-up messages
    for i, prompt in enumerate(scenario['followUpPrompts'][:scenario['maxTurns']-1], start=2):
        print(f"\n{'─'*80}")
        print(f"Turn {i}: FOLLOW-UP MESSAGE")
        print(f"{'─'*80}")
        print(f"→ User: {prompt}")
        
        response = send_message(session_id, prompt, scenario['metadata'])
        
        if "error" in response:
            print(f"❌ Failed to send message")
            break
        
        print(f"← Response: {response.get('response', 'NO RESPONSE')[:100]}...")
        print(f"   Scam Detected: {response.get('isScam', False)}")
        print(f"   Confidence: {response.get('confidence', 0):.2f}")
        
        evaluation = evaluate_response(response, i)
        results["turns"].append({
            "turn": i,
            "message": prompt,
            "response": response,
            "evaluation": evaluation
        })
        
        time.sleep(2)  # Rate limiting
    
    results["end_time"] = datetime.now(UTC).isoformat()
    
    # Calculate summary statistics
    total_turns = len(results["turns"])
    successful_responses = sum(1 for t in results["turns"] if t["evaluation"]["has_response"])
    scam_detections = sum(1 for t in results["turns"] if t["evaluation"]["is_scam_detected"])
    avg_confidence = sum(t["evaluation"]["confidence"] for t in results["turns"]) / total_turns if total_turns > 0 else 0
    total_flags = sum(t["evaluation"]["flags_detected"] for t in results["turns"])
    intelligence_turns = sum(1 for t in results["turns"] if t["evaluation"]["has_intelligence"])
    
    response_quality_issues = sum(1 for t in results["turns"] 
                                  if t["evaluation"]["response_quality"] != "good")
    
    results["summary"] = {
        "status": "completed",
        "total_turns": total_turns,
        "successful_responses": successful_responses,
        "response_rate": successful_responses / total_turns if total_turns > 0 else 0,
        "scam_detections": scam_detections,
        "scam_detection_rate": scam_detections / total_turns if total_turns > 0 else 0,
        "avg_confidence": avg_confidence,
        "total_flags_detected": total_flags,
        "intelligence_extracted_turns": intelligence_turns,
        "response_quality_issues": response_quality_issues,
        "quality_score": (successful_responses - response_quality_issues) / total_turns if total_turns > 0 else 0
    }
    
    return results


def print_summary_report(all_results: List[Dict]):
    """Print a comprehensive summary report"""
    print(f"\n\n{'='*80}")
    print(f"HACKATHON EVALUATION SUMMARY REPORT")
    print(f"{'='*80}")
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API Endpoint: {API_URL}")
    print(f"Total Scenarios Tested: {len(all_results)}")
    
    for result in all_results:
        summary = result["summary"]
        print(f"\n{'─'*80}")
        print(f"Scenario: {result['scenario_name']}")
        print(f"{'─'*80}")
        print(f"  Status: {summary.get('status', 'unknown').upper()}")
        print(f"  Total Turns: {summary.get('total_turns', 0)}")
        print(f"  Successful Responses: {summary.get('successful_responses', 0)} ({summary.get('response_rate', 0)*100:.1f}%)")
        print(f"  Scam Detections: {summary.get('scam_detections', 0)} ({summary.get('scam_detection_rate', 0)*100:.1f}%)")
        print(f"  Average Confidence: {summary.get('avg_confidence', 0):.2f}")
        print(f"  Total Flags Detected: {summary.get('total_flags_detected', 0)}")
        print(f"  Intelligence Extracted (turns): {summary.get('intelligence_extracted_turns', 0)}")
        print(f"  Response Quality Issues: {summary.get('response_quality_issues', 0)}")
        print(f"  Quality Score: {summary.get('quality_score', 0)*100:.1f}%")
        
        if summary.get('status') == 'failed':
            print(f"  ❌ Error: {summary.get('error', 'Unknown error')}")
        else:
            # Overall assessment
            if summary.get('scam_detection_rate', 0) > 0.8 and summary.get('quality_score', 0) > 0.8:
                print(f"  ✅ EXCELLENT - High detection rate and quality")
            elif summary.get('scam_detection_rate', 0) > 0.5:
                print(f"  ⚠️  GOOD - Decent detection but room for improvement")
            else:
                print(f"  ❌ NEEDS IMPROVEMENT - Low detection rate")
    
    # Overall statistics
    print(f"\n{'='*80}")
    print(f"OVERALL STATISTICS")
    print(f"{'='*80}")
    
    completed_scenarios = [r for r in all_results if r["summary"].get("status") == "completed"]
    if completed_scenarios:
        avg_detection_rate = sum(r["summary"]["scam_detection_rate"] for r in completed_scenarios) / len(completed_scenarios)
        avg_quality_score = sum(r["summary"]["quality_score"] for r in completed_scenarios) / len(completed_scenarios)
        total_turns = sum(r["summary"]["total_turns"] for r in completed_scenarios)
        total_intelligence = sum(r["summary"]["intelligence_extracted_turns"] for r in completed_scenarios)
        
        print(f"  Scenarios Completed: {len(completed_scenarios)}/{len(all_results)}")
        print(f"  Average Scam Detection Rate: {avg_detection_rate*100:.1f}%")
        print(f"  Average Quality Score: {avg_quality_score*100:.1f}%")
        print(f"  Total Conversation Turns: {total_turns}")
        print(f"  Intelligence Extraction Rate: {(total_intelligence/total_turns*100):.1f}%")
        
        # Final verdict
        print(f"\n{'─'*80}")
        if avg_detection_rate > 0.8 and avg_quality_score > 0.8:
            print(f"  🎉 FINAL VERDICT: SYSTEM PERFORMING EXCELLENTLY")
        elif avg_detection_rate > 0.6 and avg_quality_score > 0.6:
            print(f"  👍 FINAL VERDICT: SYSTEM PERFORMING WELL")
        elif avg_detection_rate > 0.4:
            print(f"  ⚠️  FINAL VERDICT: SYSTEM NEEDS OPTIMIZATION")
        else:
            print(f"  ❌ FINAL VERDICT: SYSTEM REQUIRES SIGNIFICANT IMPROVEMENT")
    else:
        print(f"  ❌ No scenarios completed successfully")
    
    print(f"{'='*80}\n")


def save_detailed_results(all_results: List[Dict], filename: str = None):
    """Save detailed results to JSON file"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"hackathon_test_results_{timestamp}.json"
    
    filepath = os.path.join(os.path.dirname(__file__), filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Detailed results saved to: {filename}")
    return filepath


def main():
    """Main test execution"""
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "HACKATHON SCENARIO EVALUATION" + " " * 28 + "║")
    print("║" + " " * 10 + "Agentic Honey-Pot for Scam Detection & Intelligence" + " " * 15 + "║")
    print("╚" + "═" * 78 + "╝")
    
    if not API_KEY:
        print("\n❌ Error: API_KEY not found")
        print("\nPlease provide your API key using one of these methods:")
        print("  1. Set API_KEY in your .env file")
        print("  2. Set environment variable: set API_KEY=your-key-here")
        print("  3. Pass as command line argument: python test_hackathon_scenarios.py YOUR_API_KEY")
        print("\nTo get your API key, check your deployment or app configuration.")
        sys.exit(1)
    
    print(f"\nAPI Endpoint: {API_URL}")
    print(f"Testing {len(SCENARIOS)} scenarios from hackathon evaluators")
    
    all_results = []
    
    for i, scenario in enumerate(SCENARIOS, 1):
        print(f"\n[{i}/{len(SCENARIOS)}] Starting scenario: {scenario['name']}")
        
        try:
            result = run_scenario_test(scenario)
            all_results.append(result)
        except Exception as e:
            print(f"\n❌ Scenario failed with exception: {e}")
            all_results.append({
                "scenario_id": scenario['scenarioId'],
                "scenario_name": scenario['name'],
                "summary": {
                    "status": "failed",
                    "error": str(e)
                }
            })
        
        # Delay between scenarios
        if i < len(SCENARIOS):
            print(f"\nWaiting 5 seconds before next scenario...")
            time.sleep(5)
    
    # Print summary report
    print_summary_report(all_results)
    
    # Save detailed results
    save_detailed_results(all_results)
    
    print("\n✅ Hackathon scenario evaluation completed!")


if __name__ == "__main__":
    main()
