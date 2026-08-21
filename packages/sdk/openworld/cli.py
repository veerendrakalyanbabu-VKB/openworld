"""OpenWorld CLI."""

import typer
from rich.console import Console
from rich.table import Table

from packages.sdk.openworld.client import OpenWorldClient

app = typer.Typer(name="openworld", help="OpenWorld CLI — The Trust Layer for the Agentic Internet")
console = Console()

agents_app = typer.Typer(help="Manage agents")
actions_app = typer.Typer(help="Manage actions")
policies_app = typer.Typer(help="Manage policies")
audit_app = typer.Typer(help="View audit logs")

app.add_typer(agents_app, name="agents")
app.add_typer(actions_app, name="actions")
app.add_typer(policies_app, name="policies")
app.add_typer(audit_app, name="audit")


def _get_client(api_url: str = "http://localhost:8000") -> OpenWorldClient:
    return OpenWorldClient(base_url=api_url)


@app.command()
def health(api_url: str = "http://localhost:8000"):
    """Check API health."""
    with _get_client(api_url) as client:
        result = client.health()
        console.print(f"[green]✓[/green] {result['service']} v{result['version']} — {result['status']}")
        if result.get("demo_mode"):
            console.print("[yellow]DEMO MODE — SYNTHETIC DATA[/yellow]")


@agents_app.command("list")
def agents_list(api_url: str = "http://localhost:8000"):
    """List all agents."""
    with _get_client(api_url) as client:
        data = client.agents.list()
        table = Table(title="Agents")
        table.add_column("Name", style="cyan")
        table.add_column("Status")
        table.add_column("Trust Score")
        table.add_column("Capabilities")
        for agent in data["agents"]:
            table.add_row(
                agent["name"],
                agent["status"],
                str(agent["trust_dimensions"]["identity"] if "trust_dimensions" in agent else "—"),
                ", ".join(agent["capabilities"][:3]),
            )
        console.print(table)


@actions_app.command("list")
def actions_list(api_url: str = "http://localhost:8000"):
    """List all actions."""
    with _get_client(api_url) as client:
        data = client.actions.list()
        table = Table(title="Actions")
        table.add_column("Agent", style="cyan")
        table.add_column("Action")
        table.add_column("Status")
        table.add_column("Risk")
        for action in data["actions"]:
            table.add_row(
                action["agent_name"],
                action["action"],
                action["status"],
                action.get("risk_level", "—") or "—",
            )
        console.print(table)


@policies_app.command("list")
def policies_list(api_url: str = "http://localhost:8000"):
    """List all policies."""
    with _get_client(api_url) as client:
        data = client.policies.list()
        table = Table(title="Policies")
        table.add_column("Name", style="cyan")
        table.add_column("Version")
        table.add_column("Rules")
        table.add_column("Enabled")
        for policy in data["policies"]:
            table.add_row(
                policy["name"],
                policy["version"],
                str(len(policy["rules"])),
                "✓" if policy["enabled"] else "✗",
            )
        console.print(table)


@audit_app.command("list")
def audit_list(api_url: str = "http://localhost:8000", limit: int = 20):
    """List audit events."""
    with _get_client(api_url) as client:
        data = client.audit.list(limit=limit)
        table = Table(title="Audit Events")
        table.add_column("Type", style="cyan")
        table.add_column("Actor")
        table.add_column("Action")
        table.add_column("Decision")
        for event in data["events"]:
            table.add_row(
                event["event_type"],
                event["actor"],
                event.get("action", "—"),
                event.get("decision", "—"),
            )
        console.print(table)


@app.command()
def demo(api_url: str = "http://localhost:8000"):
    """Run a safe deterministic demonstration."""
    console.print("\n[bold cyan]OPENWORLD DEMO[/bold cyan]")
    console.print("[yellow]DEMO MODE — SYNTHETIC DATA[/yellow]\n")

    with _get_client(api_url) as client:
        health = client.health()
        console.print(f"API Status: [green]{health['status']}[/green]\n")

        stats = client.stats()
        console.print(f"Active Agents: {stats['active_agents']}")
        console.print(f"Verified Actions: {stats['verified_actions']}")
        console.print(f"Blocked Actions: {stats['blocked_actions']}")
        console.print(f"Pending Approvals: {stats['pending_approvals']}")
        console.print(f"Avg Trust Score: {stats['avg_trust_score']}\n")

        console.print("[bold]Simulating payment action...[/bold]")
        sim = client.actions.simulate(
            agent="FinanceBot",
            action="payment.create",
            parameters={"amount": 48500, "recipient": "ABC Services"},
        )
        console.print(f"  Policy Decision: [yellow]{sim['policy']['decision']}[/yellow]")
        console.print(f"  Risk Level: [yellow]{sim['risk']['risk_level']}[/yellow]")
        console.print(f"  Reasons: {', '.join(sim['risk']['reasons'])}\n")

        console.print("[green]Demo complete.[/green]")
        console.print("Human Intent. Machine Execution. Verifiable Results.\n")


if __name__ == "__main__":
    app()
