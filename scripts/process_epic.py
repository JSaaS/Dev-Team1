#!/usr/bin/env python3
"""
Epic Processor for GitHub Actions
This script processes an Epic issue and creates Stories using the AI Dev Team.
"""
import os
import json
import sys
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

PAULA_PROMPT = """# Persona: Produkt-Paula (Product Owner)

You are Paula, a Product Owner who breaks down Epics into User Stories.

## Your Task
Given an Epic description, create 3-7 User Stories with:
1. Clear "As a [user], I want [feature], so that [benefit]" format
2. Specific acceptance criteria using Given/When/Then
3. Story point estimates (1, 2, 3, 5, 8, or 13)
4. Priority (P1=Critical, P2=High, P3=Medium, P4=Low)
5. Dependencies between stories

## Output Format
Return a JSON object with this structure:
```json
{
  "stories": [
    {
      "title": "As a user, I want to...",
      "description": "Detailed description",
      "acceptance_criteria": [
        "GIVEN ... WHEN ... THEN ...",
        "GIVEN ... WHEN ... THEN ..."
      ],
      "story_points": 5,
      "priority": "P2",
      "dependencies": []
    }
  ],
  "assumptions": ["Assumption 1", "Assumption 2"],
  "open_questions": ["Question 1", "Question 2"]
}
```

Be thorough but practical. Each story should be completable in 1-2 sprints."""


ALF_PROMPT = """# Persona: Arkitekt-Alf (Solution Architect)

You are Alf, a Solution Architect who designs system architecture.

## Your Task
Given an Epic and its Stories, provide:
1. High-level architecture overview
2. Key components and their responsibilities
3. Data flow between components
4. Technology recommendations
5. Potential risks and mitigations

## Output Format
Return a JSON object:
```json
{
  "architecture_overview": "Brief description",
  "components": [
    {
      "name": "Component Name",
      "responsibility": "What it does",
      "technology": "Recommended tech"
    }
  ],
  "data_flows": [
    "User -> API Gateway -> Auth Service -> Database"
  ],
  "risks": [
    {
      "risk": "Description",
      "mitigation": "How to address"
    }
  ],
  "adr_summary": "Key architectural decisions"
}
```"""


STINA_PROMPT = """# Persona: Strategiska-Stina (Technical Strategist)

You are Stina, a Technical Strategist who ensures alignment with goals.

## Your Task
Assess the Epic and Stories for:
1. Strategic alignment with typical business goals
2. Resource and timeline considerations
3. Risks and dependencies
4. Go/No-Go recommendation

## Output Format
Return a JSON object:
```json
{
  "strategic_alignment": "How this fits business goals",
  "recommendation": "GO" or "CONDITIONAL" or "NO-GO",
  "conditions": ["Condition 1 if CONDITIONAL"],
  "risks": [
    {
      "risk": "Description",
      "impact": "HIGH/MEDIUM/LOW",
      "mitigation": "Suggested action"
    }
  ],
  "timeline_estimate": "Rough estimate",
  "success_metrics": ["Metric 1", "Metric 2"]
}
```"""


SYNTHESIZER_PROMPT = """# Role: Synthesizer

You synthesize input from multiple personas into a coherent plan.

## Your Task
Given input from Paula (stories), Alf (architecture), and Stina (strategy):
1. Identify agreements and conflicts
2. Create a prioritized action plan
3. List open questions needing resolution
4. Provide a final summary

## Output Format
Return a JSON object:
```json
{
  "summary": "Executive summary of the plan",
  "agreements": ["What everyone agrees on"],
  "conflicts": [
    {
      "issue": "Description",
      "positions": ["Position A", "Position B"],
      "resolution": "Suggested resolution"
    }
  ],
  "action_plan": [
    {
      "action": "What to do",
      "owner": "Who should do it",
      "priority": 1
    }
  ],
  "open_questions": ["Questions needing answers"],
  "next_steps": ["Immediate next steps"]
}
```"""


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


def process_epic(issue_number: int, issue_title: str, issue_body: str):
    """Process an Epic through all personas."""
    print(f"Processing Epic #{issue_number}: {issue_title}")
    
    # Initialize clients
    openai_client = create_openai_client()
    _, repo = get_github_client()
    issue = repo.get_issue(issue_number)
    
    epic_content = f"""# Epic: {issue_title}

{issue_body}
"""
    
    # Step 1: Paula breaks down into stories
    print("🔄 Paula is breaking down the Epic into Stories...")
    paula_result = call_persona(openai_client, PAULA_PROMPT, epic_content)
    
    # Step 2: Alf designs architecture
    print("🔄 Alf is designing the architecture...")
    alf_input = f"""{epic_content}

## Stories from Paula:
{json.dumps(paula_result['stories'], indent=2)}
"""
    alf_result = call_persona(openai_client, ALF_PROMPT, alf_input)
    
    # Step 3: Stina assesses strategy
    print("🔄 Stina is assessing strategic alignment...")
    stina_input = f"""{epic_content}

## Stories:
{json.dumps(paula_result['stories'], indent=2)}

## Architecture:
{json.dumps(alf_result, indent=2)}
"""
    stina_result = call_persona(openai_client, STINA_PROMPT, stina_input)
    
    # Step 4: Synthesizer creates unified plan
    print("🔄 Synthesizer is creating the unified plan...")
    synth_input = f"""{epic_content}

## Paula's Stories:
{json.dumps(paula_result, indent=2)}

## Alf's Architecture:
{json.dumps(alf_result, indent=2)}

## Stina's Assessment:
{json.dumps(stina_result, indent=2)}
"""
    synth_result = call_persona(openai_client, SYNTHESIZER_PROMPT, synth_input)
    
    # Create summary comment on the Epic
    print("📝 Posting summary to GitHub...")
    
    summary_comment = f"""## 🤖 AI Dev Team Analysis Complete

### 📊 Strategic Assessment
**Recommendation:** {stina_result.get('recommendation', 'N/A')}

{stina_result.get('strategic_alignment', '')}

### 📋 User Stories Identified ({len(paula_result.get('stories', []))})

"""
    
    for i, story in enumerate(paula_result.get('stories', []), 1):
        summary_comment += f"""
#### Story {i}: {story['title']}
- **Points:** {story.get('story_points', '?')} | **Priority:** {story.get('priority', '?')}
- **Acceptance Criteria:** {len(story.get('acceptance_criteria', []))} items

"""
    
    summary_comment += f"""
### 🏗️ Architecture Overview
{alf_result.get('architecture_overview', 'N/A')}

**Key Components:**
"""
    
    for comp in alf_result.get('components', []):
        summary_comment += f"- **{comp['name']}**: {comp['responsibility']}\n"
    
    summary_comment += f"""

### ⚠️ Risks Identified
"""
    for risk in stina_result.get('risks', []):
        summary_comment += f"- **{risk.get('impact', 'N/A')}**: {risk['risk']}\n"
    
    summary_comment += f"""

### 📝 Summary
{synth_result.get('summary', 'N/A')}

### ✅ Next Steps
"""
    for step in synth_result.get('next_steps', []):
        summary_comment += f"- [ ] {step}\n"
    
    summary_comment += f"""

---
*Analysis completed at {datetime.utcnow().isoformat()}Z*

**Would you like me to create the Stories as separate issues?** Reply with `@ai-team create stories` to proceed.
"""
    
    issue.create_comment(summary_comment)
    
    # Create individual story issues
    print("📝 Creating Story issues...")
    story_issues = []
    
    for story in paula_result.get('stories', []):
        story_body = f"""## User Story
{story['title']}

## Description
{story.get('description', '')}

## Acceptance Criteria
"""
        for ac in story.get('acceptance_criteria', []):
            story_body += f"- [ ] {ac}\n"
        
        story_body += f"""
## Details
- **Story Points:** {story.get('story_points', '?')}
- **Priority:** {story.get('priority', '?')}
- **Dependencies:** {', '.join(story.get('dependencies', [])) or 'None'}

## Parent Epic
Relates to #{issue_number}

---
<!-- AI-DEV-TEAM-METADATA
type: story
parent_id: {issue_number}
priority: {story.get('priority', 'P3')}
-->
"""
        
        new_issue = repo.create_issue(
            title=f"[STORY] {story['title'][:80]}",
            body=story_body,
            labels=['story']
        )
        story_issues.append(new_issue)
        print(f"  Created Story #{new_issue.number}: {story['title'][:50]}...")
    
    # Update Epic with links to stories
    stories_list = "\n".join([f"- [ ] #{s.number} - {s.title}" for s in story_issues])
    issue.create_comment(f"""## 📋 Stories Created

The following Story issues have been created:

{stories_list}

---
*{len(story_issues)} stories created from this Epic*
""")
    
    print(f"✅ Epic processing complete! Created {len(story_issues)} stories.")
    return {
        "paula": paula_result,
        "alf": alf_result,
        "stina": stina_result,
        "synthesis": synth_result,
        "stories_created": [s.number for s in story_issues]
    }


if __name__ == "__main__":
    issue_number = int(get_env("ISSUE_NUMBER"))
    issue_title = get_env("ISSUE_TITLE")
    issue_body = get_env("ISSUE_BODY")
    
    result = process_epic(issue_number, issue_title, issue_body)
    print(json.dumps(result, indent=2))
