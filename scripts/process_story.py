#!/usr/bin/env python3
"""
Story Processor for GitHub Actions
This script processes a Story issue and creates Tasks using the AI Dev Team.
"""
import os
import json
import re
from datetime import datetime
from openai import OpenAI
from github import Github


def get_env(name: str, required: bool = True) -> str:
    """Get environment variable."""
    value = os.environ.get(name, "")
    if required and not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def create_openai_client() -> OpenAI:
    """Create OpenAI client."""
    return OpenAI(api_key=get_env("OPENAI_API_KEY"))


def get_github_client():
    """Get GitHub client and repo."""
    g = Github(get_env("GITHUB_TOKEN"))
    repo = g.get_repo(f"{get_env('GITHUB_OWNER')}/{get_env('GITHUB_REPO')}")
    return g, repo


# =============================================================================
# Persona Prompts
# =============================================================================

UFFE_BREAKDOWN_PROMPT = """# Persona: Utvecklar-Uffe (Software Developer)

You are Uffe, a pragmatic software developer who breaks down Stories into implementable Tasks.

## Your Task
Given a User Story with acceptance criteria, create specific development Tasks that:
1. Are small enough to complete in 1-4 hours
2. Have clear, testable deliverables
3. Include both implementation AND test tasks
4. Consider documentation needs
5. Are ordered by dependency (what needs to be done first)

## Task Types to Consider
- **Implementation tasks**: Writing the actual code
- **Test tasks**: Unit tests, integration tests
- **Documentation tasks**: README updates, API docs, code comments
- **Infrastructure tasks**: Config files, CI/CD updates
- **Review preparation**: Security considerations, architecture alignment

## Output Format
Return a JSON object:
```json
{
  "tasks": [
    {
      "title": "Short, action-oriented title",
      "description": "What needs to be done",
      "task_type": "implementation|test|documentation|infrastructure",
      "acceptance_criteria": [
        "Specific, testable criterion 1",
        "Specific, testable criterion 2"
      ],
      "estimated_hours": 2,
      "dependencies": [],
      "files_to_modify": ["src/example.py", "tests/test_example.py"],
      "assigned_to": "uffe|tina|daniel|david"
    }
  ],
  "technical_notes": "Any important technical considerations",
  "suggested_branch_name": "feature/short-description",
  "total_estimated_hours": 8
}
```

## Guidelines
- Keep tasks atomic - one clear deliverable per task
- Always include test tasks (aim for 80%+ coverage)
- Documentation is NOT optional
- Consider error handling and edge cases
- Think about security implications
"""

ALF_TASK_REVIEW_PROMPT = """# Persona: Arkitekt-Alf (Solution Architect)

You are Alf, reviewing a task breakdown for architectural soundness.

## Your Task
Review the proposed tasks and provide:
1. Architecture alignment assessment
2. Missing considerations
3. Suggested improvements
4. Risk flags

## Output Format
Return a JSON object:
```json
{
  "assessment": "APPROVED|NEEDS_CHANGES|BLOCKED",
  "architecture_notes": "How this fits the overall architecture",
  "missing_tasks": [
    {
      "title": "Missing task title",
      "reason": "Why this is needed"
    }
  ],
  "improvements": ["Suggestion 1", "Suggestion 2"],
  "risks": [
    {
      "risk": "Description",
      "severity": "HIGH|MEDIUM|LOW",
      "mitigation": "How to address"
    }
  ],
  "api_contracts": "Any API considerations",
  "data_model_notes": "Any data model considerations"
}
```
"""

SARA_SECURITY_PROMPT = """# Persona: Säkerhets-Sara (Security Engineer)

You are Sara, reviewing tasks for security implications.

## Your Task
Review the proposed tasks and flag any security concerns:
1. Input validation needs
2. Authentication/authorization requirements
3. Data protection considerations
4. Potential vulnerabilities

## Output Format
Return a JSON object:
```json
{
  "security_assessment": "APPROVED|NEEDS_SECURITY_TASKS|BLOCKED",
  "security_tasks_needed": [
    {
      "title": "Security task title",
      "reason": "Why this is needed",
      "priority": "HIGH|MEDIUM|LOW"
    }
  ],
  "checklist_items": [
    "Security check to add to acceptance criteria"
  ],
  "warnings": ["Security warning 1"],
  "owasp_considerations": ["Relevant OWASP items"]
}
```
"""


def call_persona(client: OpenAI, persona_prompt: str, user_content: str) -> dict:
    """Call a persona and get JSON response."""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": persona_prompt},
            {"role": "user", "content": user_content}
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
        max_tokens=4096
    )
    
    return json.loads(response.choices[0].message.content)


def get_parent_epic(repo, issue_body: str):
    """Try to find the parent Epic from the issue body."""
    # Look for "Relates to #123" pattern
    match = re.search(r'Relates to #(\d+)', issue_body)
    if match:
        try:
            return repo.get_issue(int(match.group(1)))
        except:
            pass
    return None


def process_story(issue_number: int, issue_title: str, issue_body: str):
    """Process a Story through the task breakdown workflow."""
    print(f"Processing Story #{issue_number}: {issue_title}")
    
    # Initialize clients
    openai_client = create_openai_client()
    _, repo = get_github_client()
    issue = repo.get_issue(issue_number)
    
    # Get parent Epic context if available
    parent_epic = get_parent_epic(repo, issue_body)
    epic_context = ""
    if parent_epic:
        epic_context = f"""
## Parent Epic Context
**Epic #{parent_epic.number}:** {parent_epic.title}

{parent_epic.body[:1000] if parent_epic.body else 'No description'}
"""
    
    story_content = f"""# Story: {issue_title}

{issue_body}

{epic_context}
"""
    
    # Post initial comment
    issue.create_comment("""## 🤖 AI Dev Team - Breaking Down Story

I'm analyzing this Story to create implementable Tasks.

**Team members working:**
- 💻 **Utvecklar-Uffe** - Creating task breakdown
- 🏗️ **Arkitekt-Alf** - Reviewing architecture alignment
- 🔒 **Säkerhets-Sara** - Checking security implications

Please wait...
""")
    
    # Step 1: Uffe breaks down into tasks
    print("🔄 Uffe is breaking down the Story into Tasks...")
    uffe_result = call_persona(openai_client, UFFE_BREAKDOWN_PROMPT, story_content)
    
    # Step 2: Alf reviews architecture
    print("🔄 Alf is reviewing architecture alignment...")
    alf_input = f"""{story_content}

## Uffe's Task Breakdown:
{json.dumps(uffe_result, indent=2)}
"""
    alf_result = call_persona(openai_client, ALF_TASK_REVIEW_PROMPT, alf_input)
    
    # Step 3: Sara reviews security
    print("🔄 Sara is reviewing security implications...")
    sara_input = f"""{story_content}

## Proposed Tasks:
{json.dumps(uffe_result['tasks'], indent=2)}
"""
    sara_result = call_persona(openai_client, SARA_SECURITY_PROMPT, sara_input)
    
    # Merge any additional tasks from Alf and Sara
    all_tasks = uffe_result.get('tasks', [])
    
    # Add missing tasks from Alf
    for missing in alf_result.get('missing_tasks', []):
        all_tasks.append({
            "title": missing['title'],
            "description": missing['reason'],
            "task_type": "implementation",
            "acceptance_criteria": [],
            "estimated_hours": 2,
            "dependencies": [],
            "files_to_modify": [],
            "assigned_to": "uffe",
            "added_by": "Arkitekt-Alf"
        })
    
    # Add security tasks from Sara
    for sec_task in sara_result.get('security_tasks_needed', []):
        all_tasks.append({
            "title": f"🔒 {sec_task['title']}",
            "description": sec_task['reason'],
            "task_type": "security",
            "acceptance_criteria": sara_result.get('checklist_items', []),
            "estimated_hours": 2,
            "dependencies": [],
            "files_to_modify": [],
            "assigned_to": "sara",
            "added_by": "Säkerhets-Sara",
            "priority": sec_task.get('priority', 'MEDIUM')
        })
    
    # Create summary comment
    print("📝 Posting summary to GitHub...")
    
    summary = f"""## 🤖 AI Dev Team - Story Breakdown Complete

### 📊 Summary
- **Total Tasks:** {len(all_tasks)}
- **Estimated Hours:** {uffe_result.get('total_estimated_hours', 'N/A')}
- **Suggested Branch:** `{uffe_result.get('suggested_branch_name', 'feature/story-' + str(issue_number))}`

### 🏗️ Architecture Assessment
**Status:** {alf_result.get('assessment', 'N/A')}

{alf_result.get('architecture_notes', '')}

### 🔒 Security Assessment  
**Status:** {sara_result.get('security_assessment', 'N/A')}

"""
    
    if sara_result.get('warnings'):
        summary += "**Warnings:**\n"
        for warning in sara_result.get('warnings', []):
            summary += f"- ⚠️ {warning}\n"
        summary += "\n"
    
    if alf_result.get('risks'):
        summary += "### ⚠️ Risks Identified\n"
        for risk in alf_result.get('risks', []):
            summary += f"- **{risk.get('severity', 'N/A')}**: {risk['risk']}\n"
        summary += "\n"
    
    summary += f"""### 📝 Technical Notes
{uffe_result.get('technical_notes', 'None')}

---
### ✅ Tasks to be Created

"""
    
    for i, task in enumerate(all_tasks, 1):
        assignee_emoji = {
            'uffe': '💻',
            'tina': '🧪', 
            'daniel': '📝',
            'david': '🚀',
            'sara': '🔒'
        }.get(task.get('assigned_to', 'uffe'), '📋')
        
        summary += f"{i}. {assignee_emoji} **{task['title']}** ({task.get('estimated_hours', '?')}h)\n"
    
    summary += f"""

---
*Analysis completed at {datetime.utcnow().isoformat()}Z*

**Creating task issues now...**
"""
    
    issue.create_comment(summary)
    
    # Create individual task issues
    print("📝 Creating Task issues...")
    task_issues = []
    
    for task in all_tasks:
        assignee_map = {
            'uffe': 'Utvecklar-Uffe',
            'tina': 'Test-Tina',
            'daniel': 'Dok-Daniel',
            'david': 'DevOps-David',
            'sara': 'Säkerhets-Sara'
        }
        
        task_body = f"""## Task Description
{task.get('description', task['title'])}

## Acceptance Criteria
"""
        for ac in task.get('acceptance_criteria', []):
            task_body += f"- [ ] {ac}\n"
        
        if not task.get('acceptance_criteria'):
            task_body += "- [ ] Task completed and working\n- [ ] Tests passing\n"
        
        task_body += f"""
## Technical Details
- **Type:** {task.get('task_type', 'implementation')}
- **Estimated Hours:** {task.get('estimated_hours', '?')}
- **Assigned To:** {assignee_map.get(task.get('assigned_to', 'uffe'), 'Utvecklar-Uffe')}

### Files to Modify
"""
        for file in task.get('files_to_modify', []):
            task_body += f"- `{file}`\n"
        
        if not task.get('files_to_modify'):
            task_body += "- TBD\n"
        
        task_body += f"""
## Dependencies
"""
        if task.get('dependencies'):
            for dep in task['dependencies']:
                task_body += f"- {dep}\n"
        else:
            task_body += "- None\n"
        
        task_body += f"""
## Parent Story
Relates to #{issue_number}

---
<!-- AI-DEV-TEAM-METADATA
type: task
parent_id: {issue_number}
task_type: {task.get('task_type', 'implementation')}
assigned_to: {task.get('assigned_to', 'uffe')}
estimated_hours: {task.get('estimated_hours', 2)}
-->
"""
        
        # Determine labels
        labels = ['task']
        if task.get('task_type') == 'test':
            labels.append('testing')
        elif task.get('task_type') == 'documentation':
            labels.append('documentation')
        elif task.get('task_type') == 'security':
            labels.append('security')
        
        if task.get('added_by'):
            task_body += f"\n*Task added by {task['added_by']}*"
        
        new_issue = repo.create_issue(
            title=f"[TASK] {task['title'][:80]}",
            body=task_body,
            labels=labels
        )
        task_issues.append(new_issue)
        print(f"  Created Task #{new_issue.number}: {task['title'][:50]}...")
    
    # Update Story with links to tasks
    tasks_list = "\n".join([f"- [ ] #{t.number} - {t.title}" for t in task_issues])
    
    # Calculate total hours
    total_hours = sum(t.get('estimated_hours', 0) for t in all_tasks)
    
    issue.create_comment(f"""## ✅ Tasks Created

The following Task issues have been created:

{tasks_list}

---
**Total Tasks:** {len(task_issues)}
**Total Estimated Hours:** {total_hours}h
**Suggested Branch:** `{uffe_result.get('suggested_branch_name', 'feature/story-' + str(issue_number))}`

---
*To start implementation, assign a task and add the `ready` label.*
""")
    
    print(f"✅ Story processing complete! Created {len(task_issues)} tasks.")
    return {
        "uffe": uffe_result,
        "alf": alf_result,
        "sara": sara_result,
        "tasks_created": [t.number for t in task_issues],
        "total_hours": total_hours
    }


if __name__ == "__main__":
    issue_number = int(get_env("ISSUE_NUMBER"))
    issue_title = get_env("ISSUE_TITLE")
    issue_body = get_env("ISSUE_BODY")
    
    result = process_story(issue_number, issue_title, issue_body)
    print(json.dumps(result, indent=2))
