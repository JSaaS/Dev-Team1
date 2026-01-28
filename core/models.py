"""
Core data models for the AI Dev Team.
Defines work items, personas, and communication protocols.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Literal, Optional
import uuid


class WorkItemType(Enum):
    EPIC = "epic"
    STORY = "story"
    TASK = "task"
    SUBTASK = "subtask"
    BUG = "bug"


class WorkItemStatus(Enum):
    BACKLOG = "backlog"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    MERGED = "merged"
    DEPLOYED = "deployed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class PersonaType(Enum):
    PRODUKT_PAULA = "produkt_paula"       # Product Owner
    STRATEGISKA_STINA = "strategiska_stina"  # Strategist
    ARKITEKT_ALF = "arkitekt_alf"         # Architect
    UTVECKLAR_UFFE = "utvecklar_uffe"     # Developer
    TEST_TINA = "test_tina"               # QA Engineer
    DOK_DANIEL = "dok_daniel"             # Technical Writer
    SAKERHETS_SARA = "sakerhets_sara"     # Security Engineer
    DEVOPS_DAVID = "devops_david"         # DevOps Engineer
    SYNTHESIZER = "synthesizer"           # Synthesizer


class ArtifactType(Enum):
    CODE = "code"
    TEST = "test"
    DOCUMENTATION = "documentation"
    COMMENT = "comment"
    ISSUE = "issue"
    PR = "pull_request"
    REVIEW = "review"
    ADR = "adr"  # Architecture Decision Record
    DIAGRAM = "diagram"
    CONFIG = "config"


class ReviewDecision(Enum):
    APPROVE = "approve"
    REQUEST_CHANGES = "request_changes"
    COMMENT = "comment"
    BLOCK = "block"


@dataclass
class Artifact:
    """Output artifact from a persona."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: ArtifactType = ArtifactType.CODE
    content: str = ""
    target_path: Optional[str] = None
    language: Optional[str] = None
    created_by: PersonaType = PersonaType.UTVECKLAR_UFFE
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)


@dataclass
class AcceptanceCriterion:
    """Acceptance criterion for a work item."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    is_met: bool = False
    verified_by: Optional[PersonaType] = None
    verified_at: Optional[datetime] = None


@dataclass
class WorkItem:
    """Represents any work item (Epic, Story, Task, etc.)."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: WorkItemType = WorkItemType.TASK
    title: str = ""
    description: str = ""
    acceptance_criteria: list[AcceptanceCriterion] = field(default_factory=list)
    
    # Relationships
    parent_id: Optional[str] = None
    children_ids: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)
    
    # Assignment & Status
    status: WorkItemStatus = WorkItemStatus.BACKLOG
    assigned_to: Optional[PersonaType] = None
    reviewers: list[PersonaType] = field(default_factory=list)
    
    # GitHub Integration
    github_issue_number: Optional[int] = None
    github_issue_url: Optional[str] = None
    github_pr_number: Optional[int] = None
    github_pr_url: Optional[str] = None
    github_branch: Optional[str] = None
    
    # Metadata
    priority: int = 3  # 1=Critical, 2=High, 3=Medium, 4=Low
    story_points: Optional[int] = None
    labels: list[str] = field(default_factory=list)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Artifacts produced
    artifacts: list[Artifact] = field(default_factory=list)
    
    def add_acceptance_criterion(self, description: str) -> AcceptanceCriterion:
        """Add an acceptance criterion."""
        criterion = AcceptanceCriterion(description=description)
        self.acceptance_criteria.append(criterion)
        return criterion
    
    def mark_criterion_met(self, criterion_id: str, verified_by: PersonaType):
        """Mark an acceptance criterion as met."""
        for criterion in self.acceptance_criteria:
            if criterion.id == criterion_id:
                criterion.is_met = True
                criterion.verified_by = verified_by
                criterion.verified_at = datetime.utcnow()
                break
    
    def all_criteria_met(self) -> bool:
        """Check if all acceptance criteria are met."""
        return all(c.is_met for c in self.acceptance_criteria)
    
    def transition_to(self, new_status: WorkItemStatus):
        """Transition work item to new status with timestamp updates."""
        if new_status == WorkItemStatus.IN_PROGRESS and self.started_at is None:
            self.started_at = datetime.utcnow()
        elif new_status in (WorkItemStatus.MERGED, WorkItemStatus.DEPLOYED):
            self.completed_at = datetime.utcnow()
        
        self.status = new_status
        self.updated_at = datetime.utcnow()


@dataclass
class FollowUpAction:
    """Action to be taken after a persona completes their work."""
    action: str
    assigned_to: PersonaType
    priority: int = 3
    work_item_id: Optional[str] = None
    description: str = ""


@dataclass
class PersonaMessage:
    """Message sent to a persona for processing."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    work_item: WorkItem = field(default_factory=WorkItem)
    action_requested: str = ""  # "review", "implement", "break_down", "assess"
    
    # Context
    repository_state: dict = field(default_factory=dict)
    related_items: list[WorkItem] = field(default_factory=list)
    conversation_history: list[dict] = field(default_factory=list)
    
    # Constraints
    deadline: Optional[datetime] = None
    max_tokens: int = 4096
    
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PersonaResponse:
    """Response from a persona after processing a message."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_id: str = ""
    persona: PersonaType = PersonaType.SYNTHESIZER
    
    # Decision
    decision: str = ""  # "complete", "approve", "request_changes", "escalate"
    reasoning: str = ""
    confidence: float = 0.8
    
    # Outputs
    artifacts: list[Artifact] = field(default_factory=list)
    follow_up_actions: list[FollowUpAction] = field(default_factory=list)
    
    # For reviews
    review_decision: Optional[ReviewDecision] = None
    review_comments: list[dict] = field(default_factory=list)
    
    # Metadata
    tokens_used: int = 0
    processing_time_ms: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class GitHubEvent:
    """Event received from GitHub webhook."""
    event_type: str  # "issues", "pull_request", "push", "issue_comment"
    action: str  # "opened", "closed", "created", etc.
    payload: dict = field(default_factory=dict)
    
    # Extracted info
    issue_number: Optional[int] = None
    pr_number: Optional[int] = None
    author: Optional[str] = None
    body: Optional[str] = None
    
    received_at: datetime = field(default_factory=datetime.utcnow)


@dataclass 
class ReviewRequest:
    """Request for code/document review."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    work_item_id: str = ""
    pr_number: int = 0
    
    # What to review
    files_changed: list[str] = field(default_factory=list)
    diff_content: str = ""
    
    # Who should review
    required_reviewers: list[PersonaType] = field(default_factory=list)
    reviews_received: list[PersonaResponse] = field(default_factory=list)
    
    # Status
    all_approved: bool = False
    blocking_issues: list[str] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=datetime.utcnow)


# Helper functions for serialization
def work_item_to_dict(item: WorkItem) -> dict:
    """Convert WorkItem to dictionary for JSON serialization."""
    return {
        "id": item.id,
        "type": item.type.value,
        "title": item.title,
        "description": item.description,
        "acceptance_criteria": [
            {
                "id": c.id,
                "description": c.description,
                "is_met": c.is_met,
                "verified_by": c.verified_by.value if c.verified_by else None,
                "verified_at": c.verified_at.isoformat() if c.verified_at else None,
            }
            for c in item.acceptance_criteria
        ],
        "parent_id": item.parent_id,
        "children_ids": item.children_ids,
        "depends_on": item.depends_on,
        "blocks": item.blocks,
        "status": item.status.value,
        "assigned_to": item.assigned_to.value if item.assigned_to else None,
        "reviewers": [r.value for r in item.reviewers],
        "github_issue_number": item.github_issue_number,
        "github_issue_url": item.github_issue_url,
        "github_pr_number": item.github_pr_number,
        "github_pr_url": item.github_pr_url,
        "github_branch": item.github_branch,
        "priority": item.priority,
        "story_points": item.story_points,
        "labels": item.labels,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "started_at": item.started_at.isoformat() if item.started_at else None,
        "completed_at": item.completed_at.isoformat() if item.completed_at else None,
    }


def work_item_to_markdown(item: WorkItem) -> str:
    """Convert WorkItem to Markdown for GitHub issues."""
    md = f"# {item.title}\n\n"
    md += f"**Type:** {item.type.value.title()}\n"
    md += f"**Status:** {item.status.value.replace('_', ' ').title()}\n"
    md += f"**Priority:** {'⚡' * (5 - item.priority)} (P{item.priority})\n"
    
    if item.assigned_to:
        md += f"**Assigned To:** {item.assigned_to.value.replace('_', ' ').title()}\n"
    
    if item.story_points:
        md += f"**Story Points:** {item.story_points}\n"
    
    md += f"\n## Description\n\n{item.description}\n"
    
    if item.acceptance_criteria:
        md += "\n## Acceptance Criteria\n\n"
        for criterion in item.acceptance_criteria:
            checkbox = "x" if criterion.is_met else " "
            md += f"- [{checkbox}] {criterion.description}\n"
    
    if item.depends_on:
        md += f"\n## Dependencies\n\nBlocked by: {', '.join(item.depends_on)}\n"
    
    return md
