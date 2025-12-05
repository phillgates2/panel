# app/modules/ai_support/ai_support.py

"""
Advanced AI-Powered Customer Support for Panel Application
Intelligent support system with chatbots
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import re
import time


@dataclass
class SupportTicket:
    """Support ticket data"""
    ticket_id: str
    user_id: str
    subject: str
    description: str
    priority: str
    status: str
    created_at: float
    resolved_at: Optional[float]


@dataclass
class KnowledgeBaseArticle:
    """Knowledge base article"""
    article_id: str
    title: str
    content: str
    tags: List[str]
    category: str


class AISupportSystem:
    """
    AI-powered customer support with automated troubleshooting
    """

    def __init__(self):
        self.knowledge_base: Dict[str, KnowledgeBaseArticle] = {}
        self.support_tickets: Dict[str, SupportTicket] = {}
        self.troubleshooting_patterns = self._load_patterns()

    def _load_patterns(self) -> Dict[str, Dict]:
        """Load troubleshooting patterns"""
        return {
            "connection_failed": {
                "patterns": [r"can't connect", r"connection refused", r"server unreachable"],
                "solution": "Check server status and firewall settings",
                "priority": "high"
            },
            "performance_issue": {
                "patterns": [r"lag", r"fps low", r"stuttering"],
                "solution": "Optimize server settings and check resource usage",
                "priority": "medium"
            }
        }

    def automated_troubleshooting(self, issue_description: str) -> Dict[str, Any]:
        """Automated issue diagnosis and resolution"""
        # Analyze issue description
        for issue_type, data in self.troubleshooting_patterns.items():
            for pattern in data["patterns"]:
                if re.search(pattern, issue_description, re.IGNORECASE):
                    return {
                        "issue_type": issue_type,
                        "solution": data["solution"],
                        "priority": data["priority"],
                        "confidence": 0.8
                    }

        return {
            "issue_type": "unknown",
            "solution": "Please provide more details or contact support",
            "priority": "low",
            "confidence": 0.0
        }

    def create_support_ticket(self, user_id: str, subject: str, description: str) -> str:
        """Create automated support ticket"""
        ticket_id = f"ticket_{int(time.time())}"

        # Auto-classify priority
        troubleshooting = self.automated_troubleshooting(description)
        priority = troubleshooting.get("priority", "medium")

        ticket = SupportTicket(
            ticket_id=ticket_id,
            user_id=user_id,
            subject=subject,
            description=description,
            priority=priority,
            status="open",
            created_at=time.time(),
            resolved_at=None
        )

        self.support_tickets[ticket_id] = ticket
        return ticket_id

    def search_knowledge_base(self, query: str) -> List[KnowledgeBaseArticle]:
        """Search knowledge base for solutions"""
        results = []
        query_lower = query.lower()

        for article in self.knowledge_base.values():
            if (query_lower in article.title.lower() or
                query_lower in article.content.lower() or
                any(query_lower in tag.lower() for tag in article.tags)):
                results.append(article)

        return results[:5]  # Return top 5 matches


# Global AI support system
ai_support_system = AISupportSystem()