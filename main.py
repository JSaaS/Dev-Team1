#!/usr/bin/env python3
"""
AI Dev Team v2 - Main Entry Point

Usage:
    # Process an Epic (breaks down into Stories)
    python main.py epic "Build a user authentication system with OAuth support"
    
    # Process a specific task
    python main.py task --file task.json
    
    # Start webhook server for GitHub events
    python main.py server --port 8080
    
    # Interactive mode
    python main.py interactive
"""
import asyncio
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from core.models import WorkItem, WorkItemType, WorkItemStatus
from workflows.orchestrator import Orchestrator, run_epic_workflow, run_task_workflow
from github_integration.client import GitHubClient, GitHubConfig


def print_banner():
    """Print the startup banner."""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                     🤖 AI Dev Team v2.0 🤖                        ║
║                                                                    ║
║  Personas:                                                        ║
║    👩‍💼 Produkt-Paula    - Product Owner                           ║
║    📊 Strategiska-Stina - Technical Strategist                    ║
║    🏗️  Arkitekt-Alf      - Solution Architect                     ║
║    💻 Utvecklar-Uffe    - Software Developer                      ║
║    🧪 Test-Tina         - QA Engineer                             ║
║    📝 Dok-Daniel        - Technical Writer                        ║
║    🔒 Säkerhets-Sara    - Security Engineer                       ║
║    🚀 DevOps-David      - DevOps Engineer                         ║
║    🔄 Synthesizer       - Integration & Synthesis                 ║
╚══════════════════════════════════════════════════════════════════╝
""")


async def process_epic(description: str, output_dir: Path):
    """Process an Epic through the full workflow."""
    print(f"\n📋 Processing Epic: {description[:50]}...")
    print("=" * 60)
    
    state = await run_epic_workflow(description)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save synthesis
    synth_file = output_dir / f"epic_synthesis_{timestamp}.md"
    with open(synth_file, "w") as f:
        f.write(f"# Epic: {description[:100]}\n\n")
        f.write(f"**Processed at:** {state.started_at.isoformat()}\n\n")
        
        for persona_type, response in state.responses.items():
            f.write(f"## {persona_type.value.replace('_', ' ').title()}\n\n")
            f.write(response.reasoning)
            f.write("\n\n---\n\n")
        
        if state.errors:
            f.write("## Errors\n\n")
            for error in state.errors:
                f.write(f"- {error}\n")
    
    print(f"\n✅ Epic processed successfully!")
    print(f"📄 Results saved to: {synth_file}")
    
    return state


async def process_task_file(task_file: Path, output_dir: Path):
    """Process a task from a JSON file."""
    with open(task_file) as f:
        task_data = json.load(f)
    
    task = WorkItem(
        type=WorkItemType.TASK,
        title=task_data["title"],
        description=task_data["description"],
    )
    
    for criterion in task_data.get("acceptance_criteria", []):
        task.add_acceptance_criterion(criterion)
    
    print(f"\n🔧 Processing Task: {task.title}")
    print("=" * 60)
    
    state = await run_task_workflow(task)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = output_dir / f"task_result_{timestamp}.md"
    
    with open(result_file, "w") as f:
        f.write(f"# Task: {task.title}\n\n")
        f.write(f"**Status:** {state.work_item.status.value}\n\n")
        
        if state.artifacts:
            f.write("## Generated Artifacts\n\n")
            for artifact in state.artifacts:
                f.write(f"### {artifact.target_path or artifact.type.value}\n\n")
                f.write(f"```{artifact.language or ''}\n")
                f.write(artifact.content)
                f.write("\n```\n\n")
    
    print(f"\n✅ Task processed!")
    print(f"📄 Results saved to: {result_file}")
    
    return state


async def interactive_mode():
    """Run in interactive mode."""
    print_banner()
    print("\n🎮 Interactive Mode - Type 'help' for commands, 'quit' to exit\n")
    
    orchestrator = Orchestrator()
    
    while True:
        try:
            user_input = input("\n🤖 AI Dev Team > ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ("quit", "exit", "q"):
                print("👋 Goodbye!")
                break
            
            if user_input.lower() == "help":
                print("""
Commands:
    epic <description>  - Process an Epic
    task <title>        - Create and process a task
    status              - Show active workflows
    help                - Show this help
    quit                - Exit
""")
                continue
            
            if user_input.lower().startswith("epic "):
                description = user_input[5:].strip()
                if description:
                    await process_epic(description, Path("."))
                else:
                    print("❌ Please provide an Epic description")
                continue
            
            if user_input.lower().startswith("task "):
                title = user_input[5:].strip()
                if title:
                    print("Enter task description (end with empty line):")
                    lines = []
                    while True:
                        line = input()
                        if not line:
                            break
                        lines.append(line)
                    
                    task = WorkItem(
                        type=WorkItemType.TASK,
                        title=title,
                        description="\n".join(lines),
                    )
                    state = await run_task_workflow(task)
                    print(f"✅ Task completed with status: {state.work_item.status.value}")
                else:
                    print("❌ Please provide a task title")
                continue
            
            if user_input.lower() == "status":
                if orchestrator.active_workflows:
                    print("\n📊 Active Workflows:")
                    for wid, state in orchestrator.active_workflows.items():
                        print(f"  - {wid[:8]}: {state.work_item.title} ({state.phase.value})")
                else:
                    print("No active workflows")
                continue
            
            print(f"❓ Unknown command: {user_input}. Type 'help' for commands.")
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def start_webhook_server(port: int):
    """Start the webhook server for GitHub events."""
    from flask import Flask, request, jsonify
    
    app = Flask(__name__)
    orchestrator = Orchestrator()
    
    @app.route("/webhook", methods=["POST"])
    def handle_webhook():
        event_type = request.headers.get("X-GitHub-Event", "")
        payload = request.json
        
        event = orchestrator.github.parse_webhook_event(event_type, payload)
        
        # Process async
        asyncio.run(orchestrator.handle_github_event(event))
        
        return jsonify({"status": "ok"})
    
    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "healthy"})
    
    print(f"🌐 Starting webhook server on port {port}...")
    app.run(host="0.0.0.0", port=port)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AI Dev Team v2 - Autonomous Development Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py epic "Build user authentication with OAuth"
    python main.py task --file task.json
    python main.py server --port 8080
    python main.py interactive
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Epic command
    epic_parser = subparsers.add_parser("epic", help="Process an Epic")
    epic_parser.add_argument("description", help="Epic description")
    epic_parser.add_argument("--output", "-o", default="./output", help="Output directory")
    
    # Task command
    task_parser = subparsers.add_parser("task", help="Process a Task")
    task_parser.add_argument("--file", "-f", required=True, help="Task JSON file")
    task_parser.add_argument("--output", "-o", default="./output", help="Output directory")
    
    # Server command
    server_parser = subparsers.add_parser("server", help="Start webhook server")
    server_parser.add_argument("--port", "-p", type=int, default=8080, help="Port number")
    
    # Interactive command
    subparsers.add_parser("interactive", help="Interactive mode")
    
    args = parser.parse_args()
    
    if args.command == "epic":
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        asyncio.run(process_epic(args.description, output_dir))
    
    elif args.command == "task":
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        asyncio.run(process_task_file(Path(args.file), output_dir))
    
    elif args.command == "server":
        start_webhook_server(args.port)
    
    elif args.command == "interactive":
        asyncio.run(interactive_mode())
    
    else:
        print_banner()
        parser.print_help()


if __name__ == "__main__":
    main()
