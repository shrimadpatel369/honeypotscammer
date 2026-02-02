from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class SenderType(str, Enum):
    """Message sender type"""
    SCAMMER = "scammer"
    USER = "user"


class ChannelType(str, Enum):
    """Communication channel type"""
    SMS = "SMS"
    WHATSAPP = "WhatsApp"
    EMAIL = "Email"
    CHAT = "Chat"


class Message(BaseModel):
    """Individual message in a conversation"""
    sender: SenderType
    text: str
    timestamp: datetime


class Metadata(BaseModel):
    """Message metadata"""
    channel: Optional[ChannelType] = ChannelType.SMS
    language: Optional[str] = "English"
    locale: Optional[str] = "IN"


class HoneypotRequest(BaseModel):
    """Incoming request to the honeypot API"""
    sessionId: str = Field(..., description="Unique session identifier")
    message: Message = Field(..., description="Current incoming message")
    conversationHistory: List[Message] = Field(
        default_factory=list,
        description="Previous messages in the conversation"
    )
    metadata: Optional[Metadata] = Field(
        default_factory=Metadata,
        description="Additional context about the message"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "sessionId": "wertyu-dfghj-ertyui",
                "message": {
                    "sender": "scammer",
                    "text": "Your bank account will be blocked today. Verify immediately.",
                    "timestamp": "2026-01-21T10:15:30Z"
                },
                "conversationHistory": [],
                "metadata": {
                    "channel": "SMS",
                    "language": "English",
                    "locale": "IN"
                }
            }
        }


class ExtractedIntelligence(BaseModel):
    """Intelligence extracted from conversation"""
    bankAccounts: List[str] = Field(default_factory=list)
    upiIds: List[str] = Field(default_factory=list)
    phishingLinks: List[str] = Field(default_factory=list)
    phoneNumbers: List[str] = Field(default_factory=list)
    suspiciousKeywords: List[str] = Field(default_factory=list)


class EngagementMetrics(BaseModel):
    """Metrics about the engagement"""
    engagementDurationSeconds: int = Field(default=0)
    totalMessagesExchanged: int = Field(default=0)


class HoneypotResponse(BaseModel):
    """Response from the honeypot API"""
    status: str = Field(default="success")
    sessionId: str
    scamDetected: bool
    reply: Optional[str] = Field(None, description="AI agent's response to continue conversation")
    shouldContinue: bool = Field(
        default=True,
        description="Whether the conversation should continue"
    )
    engagementMetrics: EngagementMetrics
    extractedIntelligence: ExtractedIntelligence
    agentNotes: str = Field(default="")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "sessionId": "wertyu-dfghj-ertyui",
                "scamDetected": True,
                "reply": "Oh no! Why would my account be blocked?",
                "shouldContinue": True,
                "engagementMetrics": {
                    "engagementDurationSeconds": 120,
                    "totalMessagesExchanged": 3
                },
                "extractedIntelligence": {
                    "bankAccounts": [],
                    "upiIds": [],
                    "phishingLinks": [],
                    "phoneNumbers": [],
                    "suspiciousKeywords": ["blocked", "verify", "immediately"]
                },
                "agentNotes": "Initial scam detection - urgency tactics detected"
            }
        }


class GuviCallbackPayload(BaseModel):
    """Payload for GUVI final result callback"""
    sessionId: str
    scamDetected: bool
    totalMessagesExchanged: int
    extractedIntelligence: ExtractedIntelligence
    agentNotes: str


# Database Models
class SessionDocument(BaseModel):
    """MongoDB session document"""
    sessionId: str
    scamDetected: bool
    conversationHistory: List[Dict[str, Any]]
    extractedIntelligence: Dict[str, Any]
    metadata: Dict[str, Any]
    startTime: datetime
    lastUpdateTime: datetime
    totalMessages: int
    status: str  # active, completed, terminated
    agentNotes: str

    class Config:
        json_schema_extra = {
            "example": {
                "sessionId": "abc123",
                "scamDetected": True,
                "conversationHistory": [],
                "extractedIntelligence": {},
                "metadata": {},
                "startTime": "2026-01-21T10:15:30Z",
                "lastUpdateTime": "2026-01-21T10:15:30Z",
                "totalMessages": 1,
                "status": "active",
                "agentNotes": ""
            }
        }
