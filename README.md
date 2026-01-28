# 🤖 AI Dev Team v2.0

An autonomous AI-powered software development team that can break down features, write code, run tests, review changes, and deploy to production.

## Vision

Transform the consultation-based AI team into a **fully autonomous development pipeline** that can:

1. ✅ Accept Epics/Features as input
2. ✅ Break them down into Stories → Tasks
3. ✅ Execute tasks (write code, documentation, tests)
4. ✅ Review work via automated and persona-based reviews
5. ✅ Push to GitHub with proper PR workflow
6. ✅ React to new work items and external triggers

## 👥 The Team

| Persona | Role | Responsibilities |
|---------|------|------------------|
| 👩‍💼 **Produkt-Paula** | Product Owner | Breaks down Epics into Stories with acceptance criteria |
| 📊 **Strategiska-Stina** | Technical Strategist | Ensures decisions align with long-term goals |
| 🏗️ **Arkitekt-Alf** | Solution Architect | Designs system architecture, creates ADRs |
| 💻 **Utvecklar-Uffe** | Software Developer | Writes production code and unit tests |
| 🧪 **Test-Tina** | QA Engineer | Writes integration tests, validates quality |
| 📝 **Dok-Daniel** | Technical Writer | Creates and maintains documentation |
| 🔒 **Säkerhets-Sara** | Security Engineer | Reviews for vulnerabilities, blocks unsafe code |
| 🚀 **DevOps-David** | DevOps Engineer | Manages CI/CD pipelines and deployment |
| 🔄 **Synthesizer** | Integration | Merges perspectives, resolves conflicts |

## 🏃 Quick Start

### Prerequisites

- Python 3.12+
- GitHub account with repository access
- OpenAI API key (for GPT-4.1)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/ai-dev-team.git
cd ai-dev-team

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Configure environment
cp config/config.example.yaml config/config.yaml
# Edit config.yaml with your settings

# Set environment variables
export GITHUB_TOKEN="your-github-token"
export GITHUB_OWNER="your-org"
export GITHUB_REPO="your-repo"
export OPENAI_API_KEY="your-openai-key"
```

### Usage

```bash
# Process an Epic (breaks down into Stories)
python main.py epic "Build a user authentication system with OAuth support"

# Process a specific task
python main.py task --file task.json

# Start webhook server for GitHub events
python main.py server --port 8080

# Interactive mode
python main.py interactive
```

## 📁 Project Structure

```
ai-dev-team/
├── main.py                 # Entry point
├── config/
│   └── config.example.yaml # Configuration template
├── core/
│   └── models.py          # Data models (WorkItem, Artifact, etc.)
├── personas/
│   └── definitions.py     # Persona implementations
├── workflows/
│   └── orchestrator.py    # Workflow coordination
├── github_integration/
│   └── client.py          # GitHub API client
├── templates/
│   └── github/
│       ├── ISSUE_TEMPLATE/
│       └── workflows/
├── docs/
│   └── architecture/
│       └── ARCHITECTURE.md
└── tests/
```

## 🔄 Workflow

### Epic → Production Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        1. EPIC CREATED                               │
│   User creates issue with [EPIC] template describing feature         │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      2. PLANNING PHASE                               │
│   Paula breaks down Epic into Stories with acceptance criteria       │
│   Stina assesses strategic fit                                       │
│   Alf designs architecture                                           │
│   Synthesizer creates unified plan                                   │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    3. IMPLEMENTATION PHASE                           │
│   For each Task:                                                     │
│   ├── Uffe creates feature branch                                    │
│   ├── Uffe implements code                                           │
│   ├── Tina writes tests                                              │
│   ├── Daniel updates documentation                                   │
│   └── Commits pushed, PR created                                     │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      4. REVIEW PHASE                                 │
│   Parallel reviews:                                                  │
│   ├── Alf: Architecture compliance                                   │
│   ├── Sara: Security review                                          │
│   ├── Tina: Test coverage                                            │
│   └── CI: Automated checks                                           │
│   Synthesizer merges reviews                                         │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       5. MERGE & DEPLOY                              │
│   If all reviews pass:                                               │
│   ├── Auto-merge to develop                                          │
│   ├── Deploy to staging                                              │
│   └── After validation: merge to main, deploy to production          │
└─────────────────────────────────────────────────────────────────────┘
```

## 🔧 Configuration

### GitHub Token Permissions

Your GitHub token needs these permissions:
- `repo` - Full control of repositories
- `workflow` - Update GitHub Actions workflows
- `write:packages` - Push to GitHub Container Registry (optional)

### Webhook Setup

1. Go to your repo → Settings → Webhooks → Add webhook
2. Payload URL: `https://your-server/webhook`
3. Content type: `application/json`
4. Events: Issues, Pull requests, Push

## 🛡️ Security

- All code changes require security review from Säkerhets-Sara
- OWASP Top 10 checked on every PR
- Secrets scanning enabled
- Dependency vulnerability scanning
- No direct pushes to protected branches

## 🤝 Contributing

1. Create an Epic or Task issue
2. The AI team will process it automatically
3. Review the generated PR
4. Provide feedback via comments
5. Merge when approved

## 📄 License

MIT License - see LICENSE file for details.

---

**Built with ❤️ by the AI Dev Team**
