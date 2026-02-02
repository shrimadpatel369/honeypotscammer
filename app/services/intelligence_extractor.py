import re
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class IntelligenceExtractorService:
    """Service for extracting scam-related intelligence from conversations"""
    
    def __init__(self):
        # Regex patterns for various intelligence types
        self.patterns = {
            "bank_account": [
                r'\b\d{9,18}\b',  # 9-18 digit account numbers
                r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # Formatted account numbers
            ],
            "upi_id": [
                r'\b[\w\.-]+@[\w\.-]+\b',  # UPI ID format (looks like email)
                r'\b\d{10}@\w+\b',  # Phone@provider format
            ],
            "phishing_link": [
                r'https?://[^\s]+',  # Any HTTP(S) URL
                r'www\.[^\s]+',  # www. URLs
                r'\b[\w-]+\.(?:com|net|org|in|xyz|tk|ml|ga|cf|gq)[^\s]*',  # Domain patterns
            ],
            "phone_number": [
                r'\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',  # International format
                r'\b[6-9]\d{9}\b',  # Indian mobile numbers
                r'\+91[-.\s]?[6-9]\d{9}\b',  # Indian mobile with country code
            ],
            "suspicious_keywords": [
                r'\b(?:urgent|immediately|expire|suspend|block|verify|confirm|activate|update|secure|alert|warning|limited time|act now|last chance)\b',
            ],
        }
    
    async def extract_intelligence(
        self,
        conversation_history: List[Dict[str, Any]],
        current_extraction: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """
        Extract intelligence from conversation
        
        Args:
            conversation_history: All messages in the conversation
            current_extraction: Previously extracted intelligence
            
        Returns:
            Updated intelligence dictionary
        """
        try:
            # Initialize with current extraction
            intelligence = {
                "bankAccounts": list(set(current_extraction.get("bankAccounts", []))),
                "upiIds": list(set(current_extraction.get("upiIds", []))),
                "phishingLinks": list(set(current_extraction.get("phishingLinks", []))),
                "phoneNumbers": list(set(current_extraction.get("phoneNumbers", []))),
                "suspiciousKeywords": list(set(current_extraction.get("suspiciousKeywords", []))),
            }
            
            # Extract from all messages (focus on scammer messages)
            for msg in conversation_history:
                if msg.get("sender") == "scammer":
                    text = msg.get("text", "")
                    
                    # Extract bank accounts
                    for pattern in self.patterns["bank_account"]:
                        matches = re.findall(pattern, text, re.IGNORECASE)
                        for match in matches:
                            cleaned = match.replace(" ", "").replace("-", "")
                            if len(cleaned) >= 9:  # Valid account number length
                                intelligence["bankAccounts"].append(match)
                    
                    # Extract UPI IDs
                    for pattern in self.patterns["upi_id"]:
                        matches = re.findall(pattern, text, re.IGNORECASE)
                        for match in matches:
                            # Filter out common email domains that aren't UPI
                            if any(upi_provider in match.lower() for upi_provider in 
                                   ['@paytm', '@ybl', '@okicici', '@oksbi', '@okhdfcbank', 
                                    '@okaxis', '@upi', '@apl', '@axl', '@ibl', '@waicici']):
                                intelligence["upiIds"].append(match)
                            elif re.match(r'\d{10}@\w+', match):  # Phone@provider format
                                intelligence["upiIds"].append(match)
                    
                    # Extract phishing links
                    for pattern in self.patterns["phishing_link"]:
                        matches = re.findall(pattern, text, re.IGNORECASE)
                        for match in matches:
                            # Skip legitimate domains
                            if not any(legit in match.lower() for legit in 
                                      ['google.com', 'microsoft.com', 'apple.com', 
                                       'gov.in', 'facebook.com', 'twitter.com']):
                                intelligence["phishingLinks"].append(match)
                    
                    # Extract phone numbers
                    for pattern in self.patterns["phone_number"]:
                        matches = re.findall(pattern, text, re.IGNORECASE)
                        for match in matches:
                            cleaned = re.sub(r'[^\d+]', '', match)
                            if len(cleaned) >= 10:  # Valid phone number length
                                intelligence["phoneNumbers"].append(match)
                    
                    # Extract suspicious keywords
                    for pattern in self.patterns["suspicious_keywords"]:
                        matches = re.findall(pattern, text, re.IGNORECASE)
                        intelligence["suspiciousKeywords"].extend(matches)
            
            # Remove duplicates and empty values
            for key in intelligence:
                intelligence[key] = list(set(filter(None, intelligence[key])))
            
            # Limit list sizes to prevent bloat
            for key in intelligence:
                intelligence[key] = intelligence[key][:20]  # Max 20 items per category
            
            logger.info(f"Extracted intelligence: {sum(len(v) for v in intelligence.values())} total items")
            
            return intelligence
            
        except Exception as e:
            logger.error(f"Error extracting intelligence: {str(e)}", exc_info=True)
            return current_extraction
    
    def score_intelligence_quality(self, intelligence: Dict[str, List[str]]) -> float:
        """
        Score the quality of extracted intelligence
        
        Returns:
            Score from 0.0 to 1.0
        """
        weights = {
            "bankAccounts": 0.3,
            "upiIds": 0.3,
            "phishingLinks": 0.2,
            "phoneNumbers": 0.1,
            "suspiciousKeywords": 0.1,
        }
        
        score = 0.0
        for key, weight in weights.items():
            count = len(intelligence.get(key, []))
            # Normalize: 1 item = 0.3, 3+ items = 1.0
            normalized = min(count / 3.0, 1.0)
            score += normalized * weight
        
        return round(score, 2)
