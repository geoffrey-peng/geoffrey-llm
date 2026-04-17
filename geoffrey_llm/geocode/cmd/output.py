"""Output formatting for REPL using rich."""

from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.panel import Panel
from rich.rule import Rule


class Output:
    """
    Output formatting using rich library.

    Provides colored/styled output for the REPL.
    """

    def __init__(self, console: Console):
        self.console = console

    @classmethod
    def create(cls) -> "Output":
        """Create a new Output instance with default console."""
        return cls(Console())

    def print(self, *args, **kwargs):
        """Print raw text."""
        self.console.print(*args, **kwargs)

    def print_markdown(self, text: str):
        """Print markdown-formatted text."""
        md = Markdown(text)
        self.console.print(md)

    def print_code(self, code: str, language: str = "python"):
        """Print syntax-highlighted code."""
        syntax = Syntax(code, language=language, theme="monokai")
        self.console.print(syntax)

    def print_panel(self, content: str, title: str = "", style: str = "blue"):
        """Print content in a panel box."""
        panel = Panel(content, title=title, border_style=style)
        self.console.print(panel)

    def print_rule(self, title: str = ""):
        """Print a horizontal rule."""
        rule = Rule(title=title) if title else Rule()
        self.console.print(rule)

    def print_error(self, message: str):
        """Print error message in red."""
        self.console.print(f"[bold red]Error:[/bold red] {message}")

    def print_warning(self, message: str):
        """Print warning message in yellow."""
        self.console.print(f"[bold yellow]Warning:[/bold yellow] {message}")

    def print_success(self, message: str):
        """Print success message in green."""
        self.console.print(f"[bold green]Success:[/bold green] {message}]")

    def print_info(self, message: str):
        """Print info message in blue."""
        self.console.print(f"[bold blue]Info:[/bold blue] {message}")

    def print_dim(self, message: str):
        """Print dimmed text."""
        self.console.print(f"[dim]{message}[/dim]")

    def print_banner(self):
        """Print the welcome banner."""
        banner = """[bold cyan]geocode[/bold cyan] - Claude Code-like coding assistant

Type [bold]exit[/bold] or [bold]quit[/bold] to end the session.
Type [bold]help[/bold] for commands.
Type [bold]/memory[/bold] for memory commands.
Type [bold]/mcp[/bold] for MCP commands."""
        self.console.print(Panel(banner, title="Welcome", border_style="cyan"))

    def print_help(self):
        """Print help message."""
        help_text = """
[bold]Commands:[/bold]
  exit, quit     End the session
  help           Show this help message
  /new           Start a new session
  /resume <id>   Resume an existing session
  /sessions      List all sessions
  /memory        Memory management commands
  /mcp           MCP server management

[bold]Slash Commands:[/bold]
  /memory save <type> <content>  Save a memory
  /memory list [type]            List memories
  /memory recall <query>         Search memories
  /mcp list                      List MCP servers
  /mcp add <name> <config>       Add MCP server
"""
        self.console.print(Panel(help_text, title="Help", border_style="green"))

    def stream_text(self, text: str):
        """Stream text token by token (for streaming responses)."""
        # For streaming, we accumulate and print incrementally
        # Rich doesn't have great streaming support, so we use basic print
        pass

    def clear(self):
        """Clear the screen."""
        self.console.clear()
