"""
GitHub Integration Module for AI Dev Team.
Handles all interactions with GitHub API including issues, PRs, branches, and webhooks.
"""
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from github import Github, GithubException
from github.Repository import Repository
from github.Issue import Issue
from github.PullRequest import PullRequest

from core.models import (
    WorkItem, WorkItemType, WorkItemStatus, PersonaType,
    GitHubEvent, Artifact, ArtifactType, work_item_to_markdown
)


@dataclass
class GitHubConfig:
    """Configuration for GitHub integration."""
    owner: str
    repo: str
    token: str
    default_branch: str = "main"
    integration_branch: str = "develop"
    
    @classmethod
    def from_env(cls) -> "GitHubConfig":
        """Load configuration from environment variables."""
        return cls(
            owner=os.environ.get("GITHUB_OWNER", ""),
            repo=os.environ.get("GITHUB_REPO", ""),
            token=os.environ.get("GITHUB_TOKEN", ""),
            default_branch=os.environ.get("GITHUB_DEFAULT_BRANCH", "main"),
            integration_branch=os.environ.get("GITHUB_INTEGRATION_BRANCH", "develop"),
        )


class GitHubClient:
    """Client for interacting with GitHub API."""
    
    LABEL_COLORS = {
        "epic": "3E4B9E",
        "story": "0E8A16",
        "task": "1D76DB",
        "bug": "D93F0B",
        "blocked": "B60205",
        "in-review": "FBCA04",
        "security": "5319E7",
        "documentation": "0075CA",
        "architecture": "006B75",
    }
    
    def __init__(self, config: GitHubConfig):
        self.config = config
        self.github = Github(config.token)
        self._repo: Optional[Repository] = None
    
    @property
    def repo(self) -> Repository:
        """Get the repository object (lazy loaded)."""
        if self._repo is None:
            self._repo = self.github.get_repo(f"{self.config.owner}/{self.config.repo}")
        return self._repo
    
    # =========================================================================
    # Label Management
    # =========================================================================
    
    def ensure_labels_exist(self):
        """Create standard labels if they don't exist."""
        existing_labels = {label.name for label in self.repo.get_labels()}
        
        for label_name, color in self.LABEL_COLORS.items():
            if label_name not in existing_labels:
                try:
                    self.repo.create_label(name=label_name, color=color)
                    print(f"Created label: {label_name}")
                except GithubException as e:
                    print(f"Failed to create label {label_name}: {e}")
    
    # =========================================================================
    # Issue Management
    # =========================================================================
    
    def create_issue_from_work_item(self, work_item: WorkItem) -> Issue:
        """Create a GitHub issue from a WorkItem."""
        body = work_item_to_markdown(work_item)
        
        # Add metadata as HTML comment for parsing later
        metadata = f"""
<!-- AI-DEV-TEAM-METADATA
work_item_id: {work_item.id}
type: {work_item.type.value}
parent_id: {work_item.parent_id or 'none'}
priority: {work_item.priority}
-->
"""
        body = metadata + body
        
        labels = [work_item.type.value] + work_item.labels
        
        issue = self.repo.create_issue(
            title=f"[{work_item.type.value.upper()}] {work_item.title}",
            body=body,
            labels=labels,
        )
        
        # Update work item with GitHub info
        work_item.github_issue_number = issue.number
        work_item.github_issue_url = issue.html_url
        
        return issue
    
    def update_issue_from_work_item(self, work_item: WorkItem):
        """Update an existing GitHub issue from a WorkItem."""
        if not work_item.github_issue_number:
            raise ValueError("WorkItem has no associated GitHub issue")
        
        issue = self.repo.get_issue(work_item.github_issue_number)
        body = work_item_to_markdown(work_item)
        
        # Preserve metadata comment
        metadata = f"""
<!-- AI-DEV-TEAM-METADATA
work_item_id: {work_item.id}
type: {work_item.type.value}
parent_id: {work_item.parent_id or 'none'}
priority: {work_item.priority}
status: {work_item.status.value}
-->
"""
        body = metadata + body
        
        issue.edit(body=body)
        
        # Update labels based on status
        current_labels = [l.name for l in issue.labels]
        new_labels = [work_item.type.value] + work_item.labels
        
        if work_item.status == WorkItemStatus.BLOCKED:
            new_labels.append("blocked")
        if work_item.status == WorkItemStatus.IN_REVIEW:
            new_labels.append("in-review")
        
        issue.edit(labels=new_labels)
    
    def add_comment_to_issue(
        self,
        issue_number: int,
        comment: str,
        persona: PersonaType
    ):
        """Add a comment to an issue as a specific persona."""
        issue = self.repo.get_issue(issue_number)
        
        # Format comment with persona attribution
        formatted_comment = f"""### 🤖 {persona.value.replace('_', ' ').title()}

{comment}

---
*This comment was generated by the AI Dev Team*
"""
        issue.create_comment(formatted_comment)
    
    def parse_work_item_from_issue(self, issue: Issue) -> Optional[WorkItem]:
        """Parse a WorkItem from a GitHub issue."""
        # Extract metadata from HTML comment
        metadata_match = re.search(
            r'<!-- AI-DEV-TEAM-METADATA\n(.*?)\n-->',
            issue.body or "",
            re.DOTALL
        )
        
        if not metadata_match:
            return None
        
        metadata_str = metadata_match.group(1)
        metadata = {}
        for line in metadata_str.strip().split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                metadata[key.strip()] = value.strip()
        
        # Determine type from labels or metadata
        work_type = WorkItemType.TASK
        for label in issue.labels:
            if label.name in [t.value for t in WorkItemType]:
                work_type = WorkItemType(label.name)
                break
        
        work_item = WorkItem(
            id=metadata.get('work_item_id', str(issue.number)),
            type=work_type,
            title=re.sub(r'^\[.*?\]\s*', '', issue.title),  # Remove [TYPE] prefix
            description=issue.body or "",
            github_issue_number=issue.number,
            github_issue_url=issue.html_url,
            labels=[l.name for l in issue.labels if l.name not in [t.value for t in WorkItemType]],
        )
        
        if metadata.get('parent_id') and metadata['parent_id'] != 'none':
            work_item.parent_id = metadata['parent_id']
        
        if metadata.get('priority'):
            work_item.priority = int(metadata['priority'])
        
        return work_item
    
    # =========================================================================
    # Branch Management
    # =========================================================================
    
    def create_feature_branch(self, work_item: WorkItem) -> str:
        """Create a feature branch for a work item."""
        # Generate branch name
        safe_title = re.sub(r'[^a-zA-Z0-9]+', '-', work_item.title.lower())[:30]
        branch_name = f"feature/{work_item.type.value}-{work_item.github_issue_number or work_item.id[:8]}-{safe_title}"
        
        # Get the SHA of the integration branch
        base_branch = self.repo.get_branch(self.config.integration_branch)
        base_sha = base_branch.commit.sha
        
        # Create the branch
        try:
            self.repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=base_sha
            )
        except GithubException as e:
            if e.status == 422:  # Branch already exists
                pass
            else:
                raise
        
        work_item.github_branch = branch_name
        return branch_name
    
    def delete_branch(self, branch_name: str):
        """Delete a branch."""
        try:
            ref = self.repo.get_git_ref(f"heads/{branch_name}")
            ref.delete()
        except GithubException:
            pass  # Branch doesn't exist
    
    # =========================================================================
    # File Operations
    # =========================================================================
    
    def commit_artifact(
        self,
        artifact: Artifact,
        branch: str,
        commit_message: str
    ) -> str:
        """Commit an artifact to a branch."""
        if not artifact.target_path:
            raise ValueError("Artifact has no target path")
        
        # Try to get existing file to update
        try:
            contents = self.repo.get_contents(artifact.target_path, ref=branch)
            result = self.repo.update_file(
                path=artifact.target_path,
                message=commit_message,
                content=artifact.content,
                sha=contents.sha,
                branch=branch
            )
        except GithubException as e:
            if e.status == 404:  # File doesn't exist, create it
                result = self.repo.create_file(
                    path=artifact.target_path,
                    message=commit_message,
                    content=artifact.content,
                    branch=branch
                )
            else:
                raise
        
        return result['commit'].sha
    
    def commit_multiple_artifacts(
        self,
        artifacts: list[Artifact],
        branch: str,
        commit_message: str
    ) -> str:
        """Commit multiple artifacts in a single commit."""
        # Get the current tree
        base_ref = self.repo.get_git_ref(f"heads/{branch}")
        base_sha = base_ref.object.sha
        base_commit = self.repo.get_git_commit(base_sha)
        base_tree = base_commit.tree
        
        # Create blobs for each artifact
        tree_elements = []
        for artifact in artifacts:
            if not artifact.target_path:
                continue
            
            blob = self.repo.create_git_blob(artifact.content, "utf-8")
            tree_elements.append({
                "path": artifact.target_path,
                "mode": "100644",
                "type": "blob",
                "sha": blob.sha
            })
        
        # Create new tree
        new_tree = self.repo.create_git_tree(tree_elements, base_tree)
        
        # Create commit
        new_commit = self.repo.create_git_commit(
            message=commit_message,
            tree=new_tree,
            parents=[base_commit]
        )
        
        # Update branch reference
        base_ref.edit(new_commit.sha)
        
        return new_commit.sha
    
    def get_file_content(self, path: str, branch: str = None) -> Optional[str]:
        """Get content of a file from the repository."""
        branch = branch or self.config.default_branch
        try:
            contents = self.repo.get_contents(path, ref=branch)
            return contents.decoded_content.decode('utf-8')
        except GithubException:
            return None
    
    # =========================================================================
    # Pull Request Management
    # =========================================================================
    
    def create_pull_request(
        self,
        work_item: WorkItem,
        title: Optional[str] = None,
        body: Optional[str] = None
    ) -> PullRequest:
        """Create a pull request for a work item."""
        if not work_item.github_branch:
            raise ValueError("WorkItem has no associated branch")
        
        pr_title = title or f"[{work_item.type.value.upper()}] {work_item.title}"
        
        pr_body = body or f"""## Summary

{work_item.description}

## Related Issue

Closes #{work_item.github_issue_number}

## Checklist

- [ ] Code follows project conventions
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Security review passed

---
*This PR was created by the AI Dev Team*
"""
        
        pr = self.repo.create_pull(
            title=pr_title,
            body=pr_body,
            head=work_item.github_branch,
            base=self.config.integration_branch
        )
        
        work_item.github_pr_number = pr.number
        work_item.github_pr_url = pr.html_url
        
        return pr
    
    def add_review_to_pr(
        self,
        pr_number: int,
        persona: PersonaType,
        body: str,
        event: str = "COMMENT"  # APPROVE, REQUEST_CHANGES, COMMENT
    ):
        """Add a review to a pull request."""
        pr = self.repo.get_pull(pr_number)
        
        review_body = f"""### 🤖 {persona.value.replace('_', ' ').title()} Review

{body}

---
*This review was generated by the AI Dev Team*
"""
        pr.create_review(body=review_body, event=event)
    
    def get_pr_diff(self, pr_number: int) -> str:
        """Get the diff content of a pull request."""
        pr = self.repo.get_pull(pr_number)
        
        files_diff = []
        for file in pr.get_files():
            files_diff.append(f"### {file.filename}\n```diff\n{file.patch or ''}\n```\n")
        
        return "\n".join(files_diff)
    
    def get_pr_files(self, pr_number: int) -> list[dict]:
        """Get list of files changed in a PR."""
        pr = self.repo.get_pull(pr_number)
        return [
            {
                "filename": f.filename,
                "status": f.status,
                "additions": f.additions,
                "deletions": f.deletions,
                "patch": f.patch
            }
            for f in pr.get_files()
        ]
    
    def merge_pull_request(
        self,
        pr_number: int,
        commit_message: Optional[str] = None,
        merge_method: str = "squash"  # merge, squash, rebase
    ):
        """Merge a pull request."""
        pr = self.repo.get_pull(pr_number)
        pr.merge(
            commit_message=commit_message,
            merge_method=merge_method
        )
    
    # =========================================================================
    # Event Parsing
    # =========================================================================
    
    def parse_webhook_event(self, event_type: str, payload: dict) -> GitHubEvent:
        """Parse a GitHub webhook event."""
        event = GitHubEvent(
            event_type=event_type,
            action=payload.get("action", ""),
            payload=payload
        )
        
        if "issue" in payload:
            event.issue_number = payload["issue"]["number"]
            event.body = payload["issue"].get("body", "")
        
        if "pull_request" in payload:
            event.pr_number = payload["pull_request"]["number"]
            event.body = payload["pull_request"].get("body", "")
        
        if "comment" in payload:
            event.body = payload["comment"].get("body", "")
        
        if "sender" in payload:
            event.author = payload["sender"]["login"]
        
        return event
    
    # =========================================================================
    # Repository State
    # =========================================================================
    
    def get_repository_state(self, branch: str = None) -> dict:
        """Get current state of the repository."""
        branch = branch or self.config.integration_branch
        
        # Get recent commits
        commits = []
        for commit in self.repo.get_commits(sha=branch)[:10]:
            commits.append({
                "sha": commit.sha[:7],
                "message": commit.commit.message.split('\n')[0],
                "author": commit.commit.author.name,
                "date": commit.commit.author.date.isoformat()
            })
        
        # Get open PRs
        open_prs = []
        for pr in self.repo.get_pulls(state="open", base=self.config.integration_branch):
            open_prs.append({
                "number": pr.number,
                "title": pr.title,
                "branch": pr.head.ref,
                "author": pr.user.login,
                "created_at": pr.created_at.isoformat()
            })
        
        # Get open issues
        open_issues = []
        for issue in self.repo.get_issues(state="open")[:20]:
            if issue.pull_request is None:  # Exclude PRs
                open_issues.append({
                    "number": issue.number,
                    "title": issue.title,
                    "labels": [l.name for l in issue.labels],
                    "created_at": issue.created_at.isoformat()
                })
        
        return {
            "branch": branch,
            "recent_commits": commits,
            "open_prs": open_prs,
            "open_issues": open_issues,
            "default_branch": self.config.default_branch,
            "integration_branch": self.config.integration_branch
        }


# Convenience function to get a configured client
def get_github_client() -> GitHubClient:
    """Get a GitHub client configured from environment variables."""
    config = GitHubConfig.from_env()
    return GitHubClient(config)
