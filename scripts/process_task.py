#!/usr/bin/env python3
"""
Task Implementation Processor for GitHub Actions
This script implements a Task by having the AI Dev Team write actual code.

Workflow:
1. Utvecklar-Uffe writes the implementation code
2. Test-Tina writes unit tests
3. Dok-Daniel writes/updates documentation
4. Code is committed to a feature branch
5. A Pull Request is created
"""
import os
import json
import re
import base64
from datetime import datetime
from openai import OpenAI
from github import Github, GithubException


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

UFFE_IMPLEMENT_PROMPT = """# Persona: Utvecklar-Uffe (Software Developer)

You are Uffe, a pragmatic software developer who writes clean, working code.

## Your Task
Implement the code for this Task. Write production-ready code that:
1. Follows Python best practices (PEP 8, type hints, docstrings)
2. Is well-structured and readable
3. Handles errors appropriately
4. Is testable

## Output Format
Return a JSON object with the files to create/modify:
```json
{
  "files": [
    {
      "path": "src/module_name.py",
      "content": "# Full file content here...",
      "action": "create|update",
      "description": "What this file does"
    }
  ],
  "implementation_notes": "Key decisions and considerations",
  "dependencies_added": ["package1", "package2"],
  "environment_variables": ["VAR_NAME"],
  "commit_message": "feat(scope): description"
}
```

## Guidelines
- Use Python 3.12+ features
- Include type hints for all functions
- Write comprehensive docstrings
- Keep functions small and focused
- Use meaningful variable names
- Handle edge cases and errors
- NO placeholder code - write complete, working implementations
"""

TINA_TEST_PROMPT = """# Persona: Test-Tina (QA Engineer)

You are Tina, a QA engineer who writes thorough tests.

## Your Task
Write unit tests for the implementation code. Create tests that:
1. Cover all public functions/methods
2. Test happy paths and edge cases
3. Test error handling
4. Aim for 80%+ coverage

## Output Format
Return a JSON object with test files:
```json
{
  "files": [
    {
      "path": "tests/test_module_name.py",
      "content": "# Full test file content...",
      "action": "create|update",
      "description": "Tests for module_name"
    }
  ],
  "test_summary": {
    "total_tests": 10,
    "test_categories": ["unit", "integration"],
    "coverage_estimate": "85%"
  },
  "testing_notes": "Important test considerations"
}
```

## Guidelines
- Use pytest as the test framework
- Use descriptive test names (test_function_does_something_when_condition)
- Use fixtures for common setup
- Test both success and failure cases
- Mock external dependencies
- Include edge case tests
"""

DANIEL_DOC_PROMPT = """# Persona: Dok-Daniel (Technical Writer)

You are Daniel, a technical writer who creates clear documentation.

## Your Task
Create/update documentation for the implementation:
1. Code docstrings (if missing)
2. README updates (if needed)
3. API documentation (if applicable)
4. Usage examples

## Output Format
Return a JSON object with documentation:
```json
{
  "files": [
    {
      "path": "docs/module_name.md",
      "content": "# Documentation content...",
      "action": "create|update",
      "description": "Documentation for module"
    }
  ],
  "readme_section": "Section to add to main README (if any)",
  "usage_examples": [
    {
      "title": "Basic usage",
      "code": "example code here"
    }
  ],
  "documentation_notes": "What was documented"
}
```

## Guidelines
- Write for developers who will use this code
- Include practical examples
- Document any configuration needed
- Explain error handling
- Keep it concise but complete
"""

REVIEW_SUMMARY_PROMPT = """# Role: Code Review Synthesizer

Summarize the implementation for the Pull Request description.

## Output Format
Return a JSON object:
```json
{
  "pr_title": "feat(scope): Short description",
  "pr_body": "Full PR description in markdown",
  "changes_summary": ["Change 1", "Change 2"],
  "testing_instructions": "How to test this",
  "checklist": [
    "Code follows style guidelines",
    "Tests added",
    "Documentation updated"
  ]
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
        temperature=0.3,  # Lower temperature for more consistent code
        max_tokens=8192   # More tokens for code generation
    )
    
    return json.loads(response.choices[0].message.content)


def get_parent_story(repo, issue_body: str):
    """Try to find the parent Story from the issue body."""
    match = re.search(r'Relates to #(\d+)', issue_body)
    if match:
        try:
            return repo.get_issue(int(match.group(1)))
        except:
            pass
    return None


def get_existing_file_content(repo, path: str, branch: str) -> str | None:
    """Get content of existing file if it exists."""
    try:
        content = repo.get_contents(path, ref=branch)
        return base64.b64decode(content.content).decode('utf-8')
    except GithubException:
        return None


def create_branch(repo, branch_name: str, base_branch: str = "main"):
    """Create a new branch from base branch."""
    try:
        base_ref = repo.get_branch(base_branch)
        repo.create_git_ref(
            ref=f"refs/heads/{branch_name}",
            sha=base_ref.commit.sha
        )
        print(f"  Created branch: {branch_name}")
        return True
    except GithubException as e:
        if e.status == 422:  # Branch already exists
            print(f"  Branch {branch_name} already exists")
            return True
        raise


def commit_file(repo, path: str, content: str, message: str, branch: str):
    """Create or update a file in the repository."""
    try:
        # Try to get existing file
        existing = repo.get_contents(path, ref=branch)
        repo.update_file(
            path=path,
            message=message,
            content=content,
            sha=existing.sha,
            branch=branch
        )
        print(f"  Updated: {path}")
    except GithubException as e:
        if e.status == 404:
            # File doesn't exist, create it
            repo.create_file(
                path=path,
                message=message,
                content=content,
                branch=branch
            )
            print(f"  Created: {path}")
        else:
            raise


def create_pull_request(repo, branch: str, base: str, title: str, body: str, issue_number: int):
    """Create a pull request."""
    try:
        pr = repo.create_pull(
            title=title,
            body=body,
            head=branch,
            base=base
        )
        print(f"  Created PR #{pr.number}: {title}")
        return pr
    except GithubException as e:
        if "A pull request already exists" in str(e):
            # Find existing PR
            prs = repo.get_pulls(head=f"{repo.owner.login}:{branch}", state='open')
            for pr in prs:
                print(f"  PR already exists: #{pr.number}")
                return pr
        raise


def process_task(issue_number: int, issue_title: str, issue_body: str):
    """Process a Task through implementation."""
    print(f"Implementing Task #{issue_number}: {issue_title}")
    
    # Initialize clients
    openai_client = create_openai_client()
    _, repo = get_github_client()
    issue = repo.get_issue(issue_number)
    
    # Get parent Story context
    parent_story = get_parent_story(repo, issue_body)
    story_context = ""
    if parent_story:
        story_context = f"""
## Parent Story Context
**Story #{parent_story.number}:** {parent_story.title}

{parent_story.body[:1500] if parent_story.body else 'No description'}
"""
    
    # Create branch name
    safe_title = re.sub(r'[^a-zA-Z0-9]+', '-', issue_title.lower())[:40]
    branch_name = f"feature/task-{issue_number}-{safe_title}".rstrip('-')
    
    task_content = f"""# Task: {issue_title}

{issue_body}

{story_context}

## Repository Context
- Language: Python
- Test Framework: pytest  
- Branch to create: {branch_name}
"""
    
    # Post initial comment
    issue.create_comment(f"""## 🤖 AI Dev Team - Implementing Task

I'm implementing this Task. Here's the plan:

1. 💻 **Utvecklar-Uffe** - Writing implementation code
2. 🧪 **Test-Tina** - Writing unit tests
3. 📝 **Dok-Daniel** - Updating documentation
4. 🔀 Creating branch `{branch_name}` and PR

Please wait while I write the code...
""")
    
    # Step 1: Uffe writes implementation
    print("🔄 Uffe is writing the implementation...")
    uffe_result = call_persona(openai_client, UFFE_IMPLEMENT_PROMPT, task_content)
    
    # Step 2: Tina writes tests
    print("🔄 Tina is writing tests...")
    tina_input = f"""{task_content}

## Uffe's Implementation:
{json.dumps(uffe_result.get('files', []), indent=2)}

Implementation notes: {uffe_result.get('implementation_notes', 'None')}
"""
    tina_result = call_persona(openai_client, TINA_TEST_PROMPT, tina_input)
    
    # Step 3: Daniel writes documentation
    print("🔄 Daniel is writing documentation...")
    daniel_input = f"""{task_content}

## Implementation Files:
{json.dumps(uffe_result.get('files', []), indent=2)}

## Test Files:
{json.dumps(tina_result.get('files', []), indent=2)}
"""
    daniel_result = call_persona(openai_client, DANIEL_DOC_PROMPT, daniel_input)
    
    # Step 4: Create PR summary
    print("🔄 Creating PR summary...")
    all_files = (
        uffe_result.get('files', []) + 
        tina_result.get('files', []) + 
        daniel_result.get('files', [])
    )
    
    pr_input = f"""{task_content}

## Files Created/Modified:
{json.dumps([{'path': f['path'], 'description': f.get('description', '')} for f in all_files], indent=2)}

## Implementation Notes:
{uffe_result.get('implementation_notes', 'None')}

## Test Summary:
{json.dumps(tina_result.get('test_summary', {}), indent=2)}

## Documentation:
{daniel_result.get('documentation_notes', 'None')}
"""
    pr_result = call_persona(openai_client, REVIEW_SUMMARY_PROMPT, pr_input)
    
    # Create branch and commit files
    print(f"📝 Creating branch and committing {len(all_files)} files...")
    
    try:
        create_branch(repo, branch_name, "main")
    except Exception as e:
        print(f"  Warning: Could not create branch: {e}")
    
    # Commit each file
    for file_info in all_files:
        try:
            commit_msg = f"feat(task-{issue_number}): {file_info.get('description', 'Add ' + file_info['path'])}"
            commit_file(
                repo,
                file_info['path'],
                file_info['content'],
                commit_msg,
                branch_name
            )
        except Exception as e:
            print(f"  Error committing {file_info['path']}: {e}")
    
    # Create Pull Request
    print("🔀 Creating Pull Request...")
    
    pr_body = f"""{pr_result.get('pr_body', 'Implementation for task')}

## 🔗 Related Issues
- Closes #{issue_number}
{f"- Related to #{parent_story.number}" if parent_story else ""}

## 📋 Changes
{chr(10).join(f"- {c}" for c in pr_result.get('changes_summary', ['See files changed']))}

## 🧪 Testing
{pr_result.get('testing_instructions', 'Run `pytest` to execute tests')}

## ✅ Checklist
{chr(10).join(f"- [ ] {c}" for c in pr_result.get('checklist', ['Code review', 'Tests pass', 'Documentation updated']))}

---
*This PR was automatically generated by the AI Dev Team* 🤖

**Implementation by:** 💻 Utvecklar-Uffe
**Tests by:** 🧪 Test-Tina  
**Documentation by:** 📝 Dok-Daniel
"""
    
    try:
        pr = create_pull_request(
            repo,
            branch_name,
            "main",
            pr_result.get('pr_title', f"feat: Implement task #{issue_number}"),
            pr_body,
            issue_number
        )
        pr_url = pr.html_url
        pr_number = pr.number
    except Exception as e:
        print(f"  Error creating PR: {e}")
        pr_url = None
        pr_number = None
    
    # Post summary comment on the task
    files_summary = "\n".join([f"- `{f['path']}` - {f.get('description', 'N/A')}" for f in all_files])
    
    summary_comment = f"""## ✅ AI Dev Team - Implementation Complete!

### 📦 Branch Created
`{branch_name}`

### 📄 Files Created/Modified
{files_summary}

### 🧪 Test Summary
- **Tests Created:** {tina_result.get('test_summary', {}).get('total_tests', 'N/A')}
- **Coverage Estimate:** {tina_result.get('test_summary', {}).get('coverage_estimate', 'N/A')}

### 🔀 Pull Request
{f"**PR #{pr_number}:** {pr_url}" if pr_url else "⚠️ Could not create PR automatically"}

### 📝 Implementation Notes
{uffe_result.get('implementation_notes', 'None')}

---
*Implementation completed at {datetime.utcnow().isoformat()}Z*

**Next Steps:**
1. Review the PR
2. Run tests locally if needed
3. Request reviews from team members
4. Merge when approved!
"""
    
    issue.create_comment(summary_comment)
    
    # Add labels
    try:
        issue.add_to_labels('implemented')
        if pr_number:
            issue.add_to_labels('has-pr')
    except:
        pass
    
    print(f"✅ Task implementation complete!")
    print(f"   Branch: {branch_name}")
    print(f"   Files: {len(all_files)}")
    print(f"   PR: #{pr_number}" if pr_number else "   PR: Not created")
    
    return {
        "branch": branch_name,
        "files": [f['path'] for f in all_files],
        "pr_number": pr_number,
        "pr_url": pr_url,
        "uffe": uffe_result,
        "tina": tina_result,
        "daniel": daniel_result
    }


if __name__ == "__main__":
    issue_number = int(get_env("ISSUE_NUMBER"))
    issue_title = get_env("ISSUE_TITLE")
    issue_body = get_env("ISSUE_BODY")
    
    result = process_task(issue_number, issue_title, issue_body)
    print(json.dumps({k: v for k, v in result.items() if k not in ['uffe', 'tina', 'daniel']}, indent=2))
