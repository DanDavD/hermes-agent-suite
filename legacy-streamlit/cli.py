import argparse
import sys
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from agents.dev_team import DevSquad
from agents.job_hunter import JobAssistant

console = Console()

def run_dev(args):
    console.print(Panel.fit("[bold cyan]Hermes 5-Agent Dev Squad[/bold cyan]", border_style="cyan"))
    squad = DevSquad()
    
    with console.status("[bold green]Executing agent squad pipeline...") as status:
        for event in squad.run_squad(args.task, args.context or ""):
            step = event["step"]
            agent = event["agent"]
            model = event["model"]
            
            if "output" in event:
                console.print(f"\n[bold green]✓ Step {step}: {agent} ({model})[/bold green]")
                console.print(Markdown(event["output"]))
                console.print("-" * 60)
            else:
                status.update(f"[bold yellow]Step {step}: {agent} is working...[/bold yellow]")

def run_jobs(args):
    console.print(Panel.fit(f"[bold magenta]Scanning for Openings: {args.keywords}[/bold magenta]", border_style="magenta"))
    assistant = JobAssistant()
    with console.status("[bold green]Querying live web and filtering..."):
        results = assistant.find_openings(args.keywords, max_results=args.limit)
    console.print(Markdown(results))

def run_intel(args):
    console.print(Panel.fit(f"[bold yellow]Mining Interview Intel: {args.target}[/bold yellow]", border_style="yellow"))
    assistant = JobAssistant()
    with console.status("[bold green]Mining Reddit and forums for candidate reports..."):
        results = assistant.mine_interview_intel(args.target)
    console.print(Markdown(results))

def main():
    parser = argparse.ArgumentParser(description="Hermes Autonomous Suite CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Dev team subparser
    dev_parser = subparsers.add_parser("dev", help="Run the 5-agent game/software dev squad")
    dev_parser.add_argument("task", type=str, help="Description of the feature, architecture, or bugfix")
    dev_parser.add_argument("--context", type=str, default="", help="Optional project context")

    # Job hunter subparser
    job_parser = subparsers.add_parser("jobs", help="Search live remote/entry job openings")
    job_parser.add_argument("keywords", type=str, default="Unity developer entry level", help="Search keywords")
    job_parser.add_argument("--limit", type=int, default=8, help="Max results")

    # Intel subparser
    intel_parser = subparsers.add_parser("intel", help="Mine real interview experiences from Reddit/forums")
    intel_parser.add_argument("target", type=str, help="Company name or role to investigate")

    args = parser.parse_args()

    if args.command == "dev":
        run_dev(args)
    elif args.command == "jobs":
        run_jobs(args)
    elif args.command == "intel":
        run_intel(args)

if __name__ == "__main__":
    main()
