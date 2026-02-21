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
                r'\b\d{8,20}\b',  # 8-20 digit account numbers (standard globally)
                r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # Formatted 16-digit accounts
                r'\b\d{2,4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{2,6}\b',  # Various formatted patterns
                r'[A-Z]{2}\d{2}[A-Z0-9]{10,30}',  # IBAN format
            ],
            "upi_id": [
                r'\b[\w\.-]+@[\w\.-]+\b',  # UPI ID format (looks like email)
                r'\b\d{10}@\w+\b',  # Phone@provider format
            ],
            "phishing_link": [
                r'https?://[^\s]+',  # Any HTTP(S) URL
                r'www\.[^\s]+',  # www. URLs
                r'\b[\w-]+\.(?:com|net|org|in|xyz|tk|ml|ga|cf|gq)[^\s]*',  # Domain patterns
                r'bit\.ly/[^\s]+',  # Shortened URLs (bit.ly)
                r'tinyurl\.com/[^\s]+',  # Shortened URLs (tinyurl)
            ],
            "phone_number": [
                r'\+?\d{1,4}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',  # International format (flexible)
                r'\b\d{10,15}\b',  # Direct 10-15 digit numbers
                r'\(\d{3}\)[-.\s]?\d{3}[-.\s]?\d{4}',  # US format (555) 123-4567
            ],
            "email_address": [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Standard email format
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
                "emailAddresses": list(set(current_extraction.get("emailAddresses", []))),
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
                            # Standard bank accounts: 8-34 digits (IBAN can be up to 34 chars)
                            if len(cleaned) >= 8 and (cleaned.isdigit() or re.match(r'^[A-Z]{2}\d{2}[A-Z0-9]+$', cleaned)):
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
                            cleaned = re.sub(r'[^\d]', '', match)  # Remove all non-digits
                            # Standard phone numbers: 7-15 digits (international standard)
                            if 7 <= len(cleaned) <= 15:
                                intelligence["phoneNumbers"].append(match)
                    
                    # Extract email addresses
                    for pattern in self.patterns["email_address"]:
                        matches = re.findall(pattern, text, re.IGNORECASE)
                        for match in matches:
                            # Filter out UPI IDs that were already captured
                            if not any(upi_provider in match.lower() for upi_provider in 
                                      ['@paytm', '@ybl', '@okicici', '@oksbi', '@okhdfcbank', 
                                       '@okaxis', '@upi', '@apl', '@axl', '@ibl', '@waicici']):
                                intelligence["emailAddresses"].append(match)
                    
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
            "emailAddresses": 0.1,
            "suspiciousKeywords": 0.1,
        }
        
        score = 0.0
        for key, weight in weights.items():
            count = len(intelligence.get(key, []))
            # Normalize: 1 item = 0.3, 3+ items = 1.0
            normalized = min(count / 3.0, 1.0)
            score += normalized * weight
        
        return round(score, 2)