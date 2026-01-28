"""
Orchestrator for AI Dev Team v2.
Coordinates workflows between personas and manages the development pipeline.
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Callable
import json

from agents import Runner

from core.models import (
    WorkItem, WorkItemType, WorkItemStatus, PersonaType,
    PersonaMessage, PersonaResponse, Artifact, ArtifactType,
    FollowUpAction, ReviewDecision, GitHubEvent, ReviewRequest
)
from personas.definitions import get_persona, get_all_personas, BasePersona
from github_integration.client import GitHubClient, GitHubConfig


class WorkflowPhase(Enum):
    """Phases of the development workflow."""
    PLANNING = "planning"
    DESIGN = "design"
    IMPLEMENTATION = "implementation"
    REVIEW = "review"
    MERGE = "merge"
    DEPLOY = "deploy"


@dataclass
class WorkflowState:
    """Current state of a workflow execution."""
    work_item: WorkItem
    phase: WorkflowPhase = WorkflowPhase.PLANNING
    responses: dict[PersonaType, PersonaResponse] = field(default_factory=dict)
    artifacts: list[Artifact] = field(default_factory=list)
    pending_actions: list[FollowUpAction] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class Orchestrator:
    """
    Main orchestrator for the AI Dev Team.
    Coordinates workflow execution, persona interactions, and GitHub integration.
    """
    
    # Required reviews per work item type
    REQUIRED_REVIEWS = {
        WorkItemType.TASK: [
            PersonaType.ARKITEKT_ALF,
            PersonaType.SAKERHETS_SARA,
        ],
        WorkItemType.BUG: [
            PersonaType.SAKERHETS_SARA,
        ],
    }
    
    def __init__(
        self,
        github_client: Optional[GitHubClient] = None,
        runner: Optional[Runner] = None
    ):
        self.github = github_client
        self.runner = runner or Runner()
        self.personas = get_all_personas()
        self.active_workflows: dict[str, WorkflowState] = {}
        self.event_handlers: dict[str, list[Callable]] = {}
    
    # =========================================================================
    # Workflow Execution
    # =========================================================================
    
    async def process_epic(self, epic: WorkItem) -> WorkflowState:
        """
        Process an Epic through the full pipeline.
        1. Paula breaks down into Stories
        2. Stina & Alf assess strategic/architectural fit
        3. Synthesizer creates unified plan
        4. Stories are created in GitHub
        """
        state = WorkflowState(work_item=epic)
        self.active_workflows[epic.id] = state
        
        try:
            # Phase 1: Paula breaks down the Epic
            state.phase = WorkflowPhase.PLANNING
            paula_response = await self._invoke_persona(
                PersonaType.PRODUKT_PAULA,
                epic,
                "break_down",
                "Break down this Epic into User Stories with acceptance criteria."
            )
            state.responses[PersonaType.PRODUKT_PAULA] = paula_response
            
            # Phase 2: Parallel strategic/architectural review
            state.phase = WorkflowPhase.DESIGN
            stina_task = self._invoke_persona(
                PersonaType.STRATEGISKA_STINA,
                epic,
                "assess",
                f"Assess strategic fit of this Epic.\n\nStories proposed:\n{paula_response.reasoning}"
            )
            alf_task = self._invoke_persona(
                PersonaType.ARKITEKT_ALF,
                epic,
                "design",
                f"Design architecture for this Epic.\n\nStories proposed:\n{paula_response.reasoning}"
            )
            
            stina_response, alf_response = await asyncio.gather(stina_task, alf_task)
            state.responses[PersonaType.STRATEGISKA_STINA] = stina_response
            state.responses[PersonaType.ARKITEKT_ALF] = alf_response
            
            # Phase 3: Synthesize
            synthesis_input = self._format_synthesis_input(state.responses)
            synth_response = await self._invoke_persona(
                PersonaType.SYNTHESIZER,
                epic,
                "synthesize",
                f"Synthesize these perspectives:\n\n{synthesis_input}"
            )
            state.responses[PersonaType.SYNTHESIZER] = synth_response
            
            # Create Stories in GitHub
            if self.github:
                await self._create_stories_from_breakdown(epic, paula_response)
            
            state.completed_at = datetime.utcnow()
            
        except Exception as e:
            state.errors.append(str(e))
            raise
        
        return state
    
    async def process_task(self, task: WorkItem) -> WorkflowState:
        """
        Process a Task through implementation and review.
        1. Create feature branch
        2. Uffe implements code
        3. Tina writes tests
        4. Daniel updates docs
        5. Parallel reviews
        6. Merge if approved
        """
        state = WorkflowState(work_item=task)
        self.active_workflows[task.id] = state
        
        try:
            # Create feature branch
            if self.github:
                branch = self.github.create_feature_branch(task)
                task.github_branch = branch
            
            # Phase 1: Implementation
            state.phase = WorkflowPhase.IMPLEMENTATION
            task.transition_to(WorkItemStatus.IN_PROGRESS)
            
            # Uffe writes code
            uffe_response = await self._invoke_persona(
                PersonaType.UTVECKLAR_UFFE,
                task,
                "implement",
                "Implement this task according to the acceptance criteria."
            )
            state.responses[PersonaType.UTVECKLAR_UFFE] = uffe_response
            state.artifacts.extend(uffe_response.artifacts)
            
            # Tina writes tests
            tina_response = await self._invoke_persona(
                PersonaType.TEST_TINA,
                task,
                "test",
                f"Write tests for this implementation:\n\n{self._summarize_artifacts(uffe_response.artifacts)}"
            )
            state.responses[PersonaType.TEST_TINA] = tina_response
            state.artifacts.extend(tina_response.artifacts)
            
            # Daniel updates docs
            daniel_response = await self._invoke_persona(
                PersonaType.DOK_DANIEL,
                task,
                "document",
                f"Update documentation for:\n\n{self._summarize_artifacts(state.artifacts)}"
            )
            state.responses[PersonaType.DOK_DANIEL] = daniel_response
            state.artifacts.extend(daniel_response.artifacts)
            
            # Commit artifacts to branch
            if self.github and task.github_branch:
                await self._commit_artifacts(state.artifacts, task.github_branch)
                pr = self.github.create_pull_request(task)
                task.github_pr_number = pr.number
            
            # Phase 2: Review
            state.phase = WorkflowPhase.REVIEW
            task.transition_to(WorkItemStatus.IN_REVIEW)
            
            review_state = await self.process_review(task)
            state.responses.update(review_state.responses)
            
            # Phase 3: Merge if approved
            if self._all_reviews_approved(state):
                state.phase = WorkflowPhase.MERGE
                if self.github and task.github_pr_number:
                    self.github.merge_pull_request(task.github_pr_number)
                task.transition_to(WorkItemStatus.MERGED)
            else:
                # Request changes - add to pending actions
                for response in state.responses.values():
                    if response.review_decision == ReviewDecision.REQUEST_CHANGES:
                        state.pending_actions.extend(response.follow_up_actions)
            
            state.completed_at = datetime.utcnow()
            
        except Exception as e:
            state.errors.append(str(e))
            raise
        
        return state
    
    async def process_review(self, work_item: WorkItem) -> WorkflowState:
        """
        Process review phase for a work item.
        Triggers parallel reviews from required personas.
        """
        state = WorkflowState(work_item=work_item, phase=WorkflowPhase.REVIEW)
        
        required_reviewers = self.REQUIRED_REVIEWS.get(work_item.type, [])
        
        # Get PR diff if available
        diff_content = ""
        if self.github and work_item.github_pr_number:
            diff_content = self.github.get_pr_diff(work_item.github_pr_number)
        
        # Parallel reviews
        review_tasks = []
        for reviewer in required_reviewers:
            review_tasks.append(
                self._invoke_persona(
                    reviewer,
                    work_item,
                    "review",
                    f"Review this PR:\n\n{diff_content}"
                )
            )
        
        responses = await asyncio.gather(*review_tasks, return_exceptions=True)
        
        for reviewer, response in zip(required_reviewers, responses):
            if isinstance(response, Exception):
                state.errors.append(f"{reviewer.value}: {str(response)}")
            else:
                state.responses[reviewer] = response
                
                # Post review to GitHub
                if self.github and work_item.github_pr_number:
                    event = "APPROVE" if response.review_decision == ReviewDecision.APPROVE else "REQUEST_CHANGES"
                    self.github.add_review_to_pr(
                        work_item.github_pr_number,
                        reviewer,
                        response.reasoning,
                        event
                    )
        
        # Synthesize reviews
        synth_response = await self._invoke_persona(
            PersonaType.SYNTHESIZER,
            work_item,
            "synthesize_reviews",
            f"Synthesize these reviews:\n\n{self._format_synthesis_input(state.responses)}"
        )
        state.responses[PersonaType.SYNTHESIZER] = synth_response
        
        return state
    
    # =========================================================================
    # Event Handling
    # =========================================================================
    
    async def handle_github_event(self, event: GitHubEvent):
        """Handle incoming GitHub events."""
        handlers = {
            ("issues", "opened"): self._handle_issue_opened,
            ("issues", "assigned"): self._handle_issue_assigned,
            ("pull_request", "opened"): self._handle_pr_opened,
            ("pull_request", "review_requested"): self._handle_review_requested,
            ("issue_comment", "created"): self._handle_comment_created,
        }
        
        handler = handlers.get((event.event_type, event.action))
        if handler:
            await handler(event)
    
    async def _handle_issue_opened(self, event: GitHubEvent):
        """Handle new issue creation."""
        if not self.github:
            return
        
        issue = self.github.repo.get_issue(event.issue_number)
        work_item = self.github.parse_work_item_from_issue(issue)
        
        if work_item:
            if work_item.type == WorkItemType.EPIC:
                await self.process_epic(work_item)
    
    async def _handle_issue_assigned(self, event: GitHubEvent):
        """Handle issue assignment."""
        pass
    
    async def _handle_pr_opened(self, event: GitHubEvent):
        """Handle new PR."""
        pass
    
    async def _handle_review_requested(self, event: GitHubEvent):
        """Handle review request."""
        pass
    
    async def _handle_comment_created(self, event: GitHubEvent):
        """Handle comment creation - check for @ai-team mentions."""
        if event.body and "@ai-team" in event.body.lower():
            # Parse command and route to appropriate persona
            pass
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    async def _invoke_persona(
        self,
        persona_type: PersonaType,
        work_item: WorkItem,
        action: str,
        instructions: str
    ) -> PersonaResponse:
        """Invoke a persona to process a work item."""
        persona = self.personas[persona_type]
        
        # Build repository state context
        repo_state = {}
        if self.github:
            repo_state = self.github.get_repository_state(work_item.github_branch)
        
        message = PersonaMessage(
            work_item=work_item,
            action_requested=action,
            repository_state=repo_state,
        )
        
        # Build prompt with context
        prompt = f"""# Context
Work Item: {work_item.title}
Type: {work_item.type.value}
Status: {work_item.status.value}

## Description
{work_item.description}

## Acceptance Criteria
{chr(10).join(f"- {c.description}" for c in work_item.acceptance_criteria)}

## Instructions
{instructions}

## Repository State
Branch: {repo_state.get('branch', 'N/A')}
Open PRs: {len(repo_state.get('open_prs', []))}
"""
        
        # Run the persona agent
        input_message = [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}]
        result = await self.runner.run(persona.agent, input_message)
        
        # Parse response
        response = PersonaResponse(
            message_id=message.id,
            persona=persona_type,
            reasoning=result.final_output,
        )
        
        return response
    
    def _format_synthesis_input(self, responses: dict[PersonaType, PersonaResponse]) -> str:
        """Format responses for synthesis."""
        parts = []
        for persona_type, response in responses.items():
            parts.append(f"## {persona_type.value.replace('_', ' ').title()}\n{response.reasoning}")
        return "\n\n".join(parts)
    
    def _summarize_artifacts(self, artifacts: list[Artifact]) -> str:
        """Create a summary of artifacts for context."""
        parts = []
        for artifact in artifacts:
            parts.append(f"- {artifact.target_path or artifact.type.value}: {len(artifact.content)} chars")
        return "\n".join(parts) if parts else "No artifacts yet."
    
    async def _commit_artifacts(self, artifacts: list[Artifact], branch: str):
        """Commit artifacts to a branch."""
        if not self.github:
            return
        
        code_artifacts = [a for a in artifacts if a.target_path]
        if not code_artifacts:
            return
        
        commit_message = f"feat: implement changes\n\n" + "\n".join(
            f"- {a.target_path}" for a in code_artifacts
        )
        
        self.github.commit_multiple_artifacts(code_artifacts, branch, commit_message)
    
    async def _create_stories_from_breakdown(
        self,
        epic: WorkItem,
        paula_response: PersonaResponse
    ):
        """Create GitHub issues for stories from Paula's breakdown."""
        if not self.github:
            return
        # TODO: Parse structured output from Paula's response
        pass
    
    def _all_reviews_approved(self, state: WorkflowState) -> bool:
        """Check if all required reviews are approved."""
        required = self.REQUIRED_REVIEWS.get(state.work_item.type, [])
        
        for reviewer in required:
            response = state.responses.get(reviewer)
            if not response or response.review_decision != ReviewDecision.APPROVE:
                return False
        
        return True


# =============================================================================
# Convenience Functions
# =============================================================================

async def run_epic_workflow(epic_description: str) -> WorkflowState:
    """Run the full Epic workflow."""
    epic = WorkItem(
        type=WorkItemType.EPIC,
        title=epic_description[:100],
        description=epic_description,
    )
    
    orchestrator = Orchestrator()
    return await orchestrator.process_epic(epic)


async def run_task_workflow(task: WorkItem) -> WorkflowState:
    """Run the full Task workflow."""
    orchestrator = Orchestrator()
    return await orchestrator.process_task(task)
