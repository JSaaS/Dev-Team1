# AI Dev Team v2.0 - Architecture Document

## Vision

Transform the consultation-based AI team into a **fully autonomous development pipeline** that can:
1. Accept Epics/Features as input
2. Break them down into smaller work items (Stories → Tasks)
3. Execute tasks (write code, documentation, tests)
4. Review work via automated and persona-based reviews
5. Push to GitHub with proper PR workflow
6. React to new work items and external triggers

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ORCHESTRATOR (main.py)                            │
│  Manages workflow state, triggers personas, handles GitHub events           │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          ▼                           ▼                           ▼
┌─────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
│  PLANNING PHASE │      │   EXECUTION PHASE   │      │    REVIEW PHASE     │
│                 │      │                     │      │                     │
│ • Epic → Stories│      │ • Code Generation   │      │ • Code Review       │
│ • Stories→Tasks │      │ • Doc Generation    │      │ • Security Review   │
│ • Task Assignment│     │ • Test Generation   │      │ • Architecture Rev  │
└─────────────────┘      └─────────────────────┘      └─────────────────────┘
          │                           │                           │
          └───────────────────────────┼───────────────────────────┘
                                      ▼
                    ┌─────────────────────────────────┐
                    │         GITHUB INTERFACE        │
                    │  • Create Issues / PRs          │
                    │  • Push Commits                 │
                    │  • React to Webhooks            │
                    │  • Manage Branch Strategy       │
                    └─────────────────────────────────┘
```

---

## Persona Roles (Expanded)

### 1. **Produkt-Paula** (NEW - Product Owner)
- **Primary Mission**: Break down Epics into Stories with acceptance criteria
- **Focus**: Business value, user needs, priority
- **Outputs**: User Stories with acceptance criteria
- **GitHub Actions**: Creates Issues with `story` label

### 2. **Strategiska-Stina** (Enhanced)
- **Primary Mission**: Ensure decisions are aligned with long-term goals
- **Focus**: Roadmap alignment, risk assessment, resource planning
- **Outputs**: Strategic assessments, go/no-go recommendations
- **GitHub Actions**: Comments on PRs with strategic concerns, labels priority

### 3. **Arkitekt-Alf** (Enhanced)
- **Primary Mission**: Define technical architecture, create system documentation
- **Focus**: System boundaries, contracts, integration patterns
- **Outputs**: Architecture Decision Records (ADRs), diagrams, API contracts
- **GitHub Actions**: Creates `/docs/architecture/` files, reviews for architectural compliance

### 4. **Utvecklar-Uffe** (Enhanced → Full Developer)
- **Primary Mission**: Write production code and unit tests
- **Focus**: Implementation, code quality, testability
- **Outputs**: Source code, unit tests, inline documentation
- **GitHub Actions**: Creates feature branches, commits code, opens PRs

### 5. **Test-Tina** (NEW - QA Engineer)
- **Primary Mission**: Write integration tests, test plans, verify quality
- **Focus**: Test coverage, edge cases, regression prevention
- **Outputs**: Test files, test reports, bug reports
- **GitHub Actions**: Adds tests to PRs, creates bug issues

### 6. **Dok-Daniel** (NEW - Technical Writer)
- **Primary Mission**: Create and maintain documentation
- **Focus**: README files, API docs, user guides, changelogs
- **Outputs**: Markdown documentation, code comments
- **GitHub Actions**: Updates `/docs/`, adds docstrings

### 7. **Säkerhets-Sara** (NEW - Security Engineer)
- **Primary Mission**: Security review, vulnerability assessment
- **Focus**: OWASP, secrets management, input validation, dependencies
- **Outputs**: Security review comments, remediation tasks
- **GitHub Actions**: Reviews PRs for security, blocks unsafe merges

### 8. **DevOps-David** (NEW - DevOps Engineer)
- **Primary Mission**: CI/CD pipelines, deployment, infrastructure
- **Focus**: Automation, reliability, monitoring
- **Outputs**: GitHub Actions workflows, Dockerfiles, IaC
- **GitHub Actions**: Manages `.github/workflows/`, reviews infra changes

### 9. **Synthesizer** (Enhanced)
- **Primary Mission**: Merge perspectives, resolve conflicts, create summaries
- **Focus**: Consensus building, decision documentation
- **Outputs**: Sprint summaries, decision logs, conflict resolutions
- **GitHub Actions**: Creates summary issues, updates project boards

---

## Work Item Hierarchy

```
Epic
├── Story (user-facing feature)
│   ├── Task (implementable unit)
│   │   ├── Subtask (atomic action)
│   │   └── Subtask
│   ├── Task
│   └── Task
├── Story
└── Story
```

### Work Item States
```
BACKLOG → READY → IN_PROGRESS → IN_REVIEW → APPROVED → MERGED → DEPLOYED
```

---

## GitHub Integration Architecture

### Repository Structure
```
repo/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                 # Build, test, lint
│   │   ├── ai-team-trigger.yml    # Webhook handler for AI team
│   │   └── security-scan.yml      # Dependency & code scanning
│   ├── ISSUE_TEMPLATE/
│   │   ├── epic.md
│   │   ├── story.md
│   │   ├── task.md
│   │   └── bug.md
│   └── PULL_REQUEST_TEMPLATE.md
├── docs/
│   ├── architecture/
│   │   ├── ADR/                   # Architecture Decision Records
│   │   └── diagrams/
│   ├── api/
│   └── guides/
├── src/
├── tests/
│   ├── unit/
│   └── integration/
└── infra/
```

### Branch Strategy
```
main (protected)
├── develop (integration branch)
│   ├── feature/STORY-123-user-login
│   ├── feature/STORY-124-password-reset
│   └── bugfix/BUG-45-null-check
└── release/v1.0.0
```

### PR Workflow
```
1. Utvecklar-Uffe creates feature branch
2. Uffe commits code + tests
3. Uffe opens PR → triggers review pipeline
4. Parallel reviews:
   ├── Arkitekt-Alf: Architecture review
   ├── Säkerhets-Sara: Security review
   ├── Test-Tina: Test coverage review
   └── CI: Automated checks
5. Synthesizer merges reviews into approval/changes-requested
6. If approved → auto-merge to develop
7. If changes-requested → Uffe addresses feedback → re-review
```

---

## Event-Driven Architecture

### Triggers (Inputs)
| Event | Source | Action |
|-------|--------|--------|
| New Epic created | GitHub Issue | Paula breaks down into Stories |
| New Story created | GitHub Issue | Alf designs, Uffe estimates |
| Task assigned | GitHub Issue | Assigned persona executes |
| PR opened | GitHub PR | Review personas activate |
| PR comment | GitHub PR | Affected persona responds |
| Merge to develop | GitHub merge | DevOps-David deploys to staging |
| Schedule (daily) | Cron | Stina creates sprint summary |

### Message Queue Structure
```python
@dataclass
class WorkItem:
    id: str
    type: Literal["epic", "story", "task", "bug"]
    title: str
    description: str
    acceptance_criteria: list[str]
    assigned_to: str | None
    status: str
    parent_id: str | None
    github_issue_url: str
    created_at: datetime
    updated_at: datetime
```

---

## Persona Communication Protocol

### Input/Output Contract
Each persona receives and produces structured messages:

```yaml
# Input to Persona
message:
  context:
    work_item: WorkItem
    repository_state:
      branch: str
      recent_commits: list[Commit]
      open_prs: list[PR]
    related_items: list[WorkItem]
  action_requested: str  # "review", "implement", "break_down", etc.
  constraints:
    deadline: datetime | None
    dependencies: list[str]

# Output from Persona
response:
  decision: str  # "approve", "request_changes", "complete", etc.
  reasoning: str
  artifacts:
    - type: "code" | "documentation" | "comment" | "issue"
      content: str
      target_path: str | None
  follow_up_actions:
    - action: str
      assigned_to: str
      priority: int
```

---

## Implementation Plan

### Phase 1: GitHub Foundation
1. Set up GitHub API client with PyGithub
2. Create issue/PR templates
3. Implement webhook listener
4. Create branch management utilities

### Phase 2: Enhanced Personas
1. Extend existing personas with GitHub actions
2. Add new personas (Paula, Tina, Daniel, Sara, David)
3. Define input/output schemas per persona

### Phase 3: Orchestration
1. Build event router
2. Implement work item state machine
3. Create conflict resolution logic
4. Add parallel execution with dependency handling

### Phase 4: Execution Engine
1. Code generation integration
2. Documentation generation
3. Test generation
4. File system → GitHub commit pipeline

### Phase 5: Review Pipeline
1. Automated review triggers
2. Multi-persona review aggregation
3. Approval workflow
4. Auto-merge conditions

---

## Configuration

```yaml
# config.yaml
github:
  owner: "your-org"
  repo: "your-repo"
  default_branch: "main"
  integration_branch: "develop"

personas:
  arkitekt_alf:
    model: "gpt-4.1"
    temperature: 0.7
    review_types: ["architecture", "design"]
  utvecklar_uffe:
    model: "gpt-4.1"
    temperature: 0.3  # Lower for more deterministic code
    languages: ["python", "typescript"]
  sakerhets_sara:
    model: "gpt-4.1"
    temperature: 0.5
    security_standards: ["owasp", "cwe"]

workflow:
  require_reviews: 2
  auto_merge: true
  ci_required: true
  branch_protection: true
```

---

## Security Considerations

1. **GitHub Token Management**: Use fine-grained PATs with minimal permissions
2. **Code Review Gates**: No direct pushes to protected branches
3. **Secrets Scanning**: Automated scanning in CI pipeline
4. **Dependency Auditing**: Regular dependency vulnerability checks
5. **Rate Limiting**: Handle GitHub API rate limits gracefully
6. **Audit Logging**: All AI actions logged with reasoning

---

## Next Steps

1. Review this architecture with you
2. Get GitHub repository details (or create new one)
3. Implement Phase 1: GitHub Foundation
4. Iteratively build out remaining phases
