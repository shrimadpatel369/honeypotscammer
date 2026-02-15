from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum
import uuid


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
    
    class Config:
        extra = "allow"


class Metadata(BaseModel):
    """Message metadata"""
    channel: Optional[ChannelType] = ChannelType.SMS
    language: Optional[str] = "English"
    locale: Optional[str] = "IN"
    
    class Config:
        extra = "allow"


class HoneypotRequest(BaseModel):
    """Incoming request to the honeypot API"""
    sessionId: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique session identifier")
    message: Union[str, Message] = Field(..., description="Current incoming message")
    conversationHistory: List[Message] = Field(
        default_factory=list,
        description="Previous messages in the conversation"
    )
    metadata: Optional[Metadata] = Field(
        default=None,
        description="Additional context about the message"
    )
    
    @field_validator('message', mode='before')
    @classmethod
    def convert_message(cls, v):
        """Convert string message to Message object"""
        if isinstance(v, str):
            return Message(
                sender=SenderType.SCAMMER,
                text=v,
                timestamp=datetime.utcnow()
            )
        return v

    class Config:
        extra = "allow"
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
    emailAddresses: List[str] = Field(default_factory=list)
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


class CallbackResponse(BaseModel):
    """MongoDB callback response document - Dynamic/Loose structure"""
    sessionId: str
    callbackUrl: str
    sentPayload: Dict[str, Any]
    responseStatus: int
    responseBody: Union[str, Dict[str, Any], List[Any], Any] = Field(
        default=None,
        description="Flexible response body - can be string, JSON object, array, or any data type"
    )
    responseHeaders: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="HTTP response headers"
    )
    sentTime: datetime
    success: bool
    error: Optional[str] = None
    rawResponse: Optional[str] = Field(
        default=None,
        description="Raw response string for reference"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the callback"
    )

    class Config:
        extra = "allow"  # Allow extra fields for flexibility
        json_schema_extra = {
            "example": {
                "sessionId": "abc123",
                "callbackUrl": "https://guvi.example.com/callback",
                "sentPayload": {
                    "sessionId": "abc123",
                    "scamDetected": True,
                    "totalMessagesExchanged": 5
                },
                "responseStatus": 200,
                "responseBody": {
                    "status": "received",
                    "id": "callback-123",
                    "timestamp": "2026-01-21T10:15:30Z",
                    "custom_field": "any_value"
                },
                "responseHeaders": {
                    "content-type": "application/json",
                    "x-custom-header": "value"
                },
                "sentTime": "2026-01-21T10:15:30Z",
                "success": True,
                "error": None,
                "metadata": {
                    "retryCount": 0,
                    "processingTime": 1.23
                }
            }
        }
