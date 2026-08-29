"""Main REPL implementation for geocode."""

import asyncio
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console

from geoffrey_llm.geocode.cmd.output import Output
from geoffrey_llm.geocode.cmd.history import History
from geoffrey_llm.geocode.cmd.keybindings import Keybindings
from geoffrey_llm.geocode.models.base import BaseModel, ModelConfig, get_registry
from geoffrey_llm.geocode.tools.base import ToolRegistry, get_tool_registry
from geoffrey_llm.geocode.prompts.builder import SystemPromptBuilder
from geoffrey_llm.geocode.session.manager import SessionManager, Session
from geoffrey_llm.agent import Agent, DEFAULT_MAX_ITERATIONS


class REPL:
    """
    Interactive REPL for geocode.

    Chat handling is delegated to the geoffrey_llm.agent loop, which keeps
    calling the model until it stops requesting tools (or hits the iteration
    budget). The REPL only owns input, output rendering and sessions.
    """

    def __init__(
        self,
        model: BaseModel,
        tools: Optional[ToolRegistry] = None,
        session: Optional[Session] = None,
        config: Optional[dict] = None,
    ):
        self.model = model
        self.tools = tools or get_tool_registry()
        self.session = session
        self.config = config or {}

        # Initialize components
        self.console = Console()
        self.output = Output(self.console)
        self.history = History()
        self.keybindings = Keybindings()

        # Session manager
        self.session_manager = SessionManager()

        # Prompt builder
        self.prompt_builder = SystemPromptBuilder()

        # Message history for current conversation
        self.messages: list[dict] = []

        # Agent loop (chat turns are delegated to it)
        self.agent = Agent(
            model=self.model,
            tools=self.tools,
            max_iterations=self.config.get("max_iterations", DEFAULT_MAX_ITERATIONS),
        )

    async def run(self):
        """Run the main REPL loop."""
        self.output.print_banner()

        while True:
            try:
                # Get user input
                user_input = await self._get_input()
                if not user_input.strip():
                    continue

                # Add to history
                self.history.add(user_input)

                # Handle commands
                if user_input.lower() in ("exit", "quit"):
                    self.output.print_info("Goodbye!")
                    break

                if user_input.lower() == "help":
                    self.output.print_help()
                    continue

                if user_input.startswith("/"):
                    await self._handle_command(user_input)
                    continue

                # Process as chat input
                await self._handle_chat(user_input)

            except KeyboardInterrupt:
                self.output.print("\n[yellow]Interrupted (Ctrl+C to exit)[/yellow]")
                continue
            except EOFError:
                self.output.print_info("\nGoodbye!")
                break
            except Exception as e:
                self.output.print_error(f"Error: {str(e)}")

    async def _get_input(self) -> str:
        """Get input from user."""
        try:
            # Try prompt_toolkit if available
            try:
                from prompt_toolkit import PromptSession
                from prompt_toolkit.history import FileHistory

                session = PromptSession(
                    history=self.history.get_prompt_toolkit_history(),
                    key_bindings=self.keybindings.get_bindings(),
                )
                return await session.prompt_async(">>> ")
            except ImportError:
                # Fallback to simple input
                return await asyncio.get_event_loop().run_in_executor(
                    None, input, ">>> "
                )
        except (KeyboardInterrupt, EOFError):
            raise

    async def _handle_command(self, command: str):
        """Handle slash commands."""
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "/new":
            self.session = self.session_manager.create()
            self.messages = []
            self.output.print_success(f"New session created: {self.session.id}")

        elif cmd == "/sessions":
            sessions = self.session_manager.list()
            if not sessions:
                self.output.print_info("No sessions found")
            else:
                for s in sessions[:10]:
                    self.output.print(f"  {s.id} - {s.last_active}")

        elif cmd.startswith("/resume"):
            if not args:
                self.output.print_error("Usage: /resume <session_id>")
            else:
                session = self.session_manager.resume(args)
                if session:
                    self.session = session
                    self.messages = session.messages
                    self.output.print_success(f"Resumed session: {session.id}")
                else:
                    self.output.print_error(f"Session not found: {args}")

        elif cmd == "/memory":
            await self._handle_memory_command(args)

        elif cmd == "/mcp":
            await self._handle_mcp_command(args)

        else:
            self.output.print_error(f"Unknown command: {cmd}")

    async def _handle_chat(self, user_input: str):
        """Process chat input through the agent loop (tools loop until final answer)."""
        self.messages.append({"role": "user", "content": user_input})
        system_prompt = self._build_system_prompt()

        completed = False
        try:
            async for event in self.agent.astream(
                user_input, history=self.messages[:-1], instructions=system_prompt
            ):
                if event.type == "assistant" and event.content:
                    self.output.print_markdown(event.content)
                elif event.type == "tool_result" and event.result is not None:
                    self.output.print_dim(
                        f"\n[{event.tool_name}] {event.result.output or event.result.error}\n"
                    )
                elif event.type == "final":
                    if event.content:
                        self.output.print_markdown(event.content)
                elif event.type == "max_iterations":
                    self.output.print_error(
                        f"已达最大循环次数 ({self.agent.max_iterations}),本轮停止。"
                    )
            completed = True
        finally:
            if completed:
                self.messages = self.agent.history
                if self.session:
                    self.session.messages = self.messages
                    self.session_manager.save(self.session)
            # 异常中断时保留当前轮消息,便于用户重试。

    def _build_system_prompt(self) -> str:
        """Build the system prompt with tools and context."""
        parts = []

        # Basic instructions
        parts.append("""You are geocode, an AI coding assistant.
You help users write, edit, and understand code.
You have access to tools for reading and writing files, executing shell commands, and more.

When using tools:
1. Use FileRead to view files before editing them
2. Use FileEdit for targeted text replacements
3. Use FileWrite to create or overwrite files
4. Use Bash for shell commands (git, ls, grep, etc.)

Be concise and helpful.""")

        # Add tools section
        tool_defs = self.tools.list_tools()
        if tool_defs:
            tool_desc = "\n\n## Available Tools\n\n"
            for tool in tool_defs:
                tool_desc += f"### {tool.name}\n"
                tool_desc += f"{tool.description}\n\n"
            parts.append(tool_desc)

        return "\n\n".join(parts)

    async def _handle_memory_command(self, args: str):
        """Handle memory-related commands."""
        parts = args.split(maxsplit=2)
        subcmd = parts[0].lower() if parts else ""

        if subcmd == "save":
            if len(parts) < 3:
                self.output.print_error("Usage: /memory save <type> <content>")
                return
            memory_type = parts[1]
            content = parts[2]
            self.output.print_success(f"Saved {memory_type} memory: {content[:50]}...")

        elif subcmd == "list":
            self.output.print_info("Memory entries (placeholder)")

        elif subcmd == "recall":
            if not parts[1:]:
                self.output.print_error("Usage: /memory recall <query>")
                return
            self.output.print_info(f"Searching memories for: {parts[1]}")

        else:
            self.output.print_info("Memory commands: save, list, recall")

    async def _handle_mcp_command(self, args: str):
        """Handle MCP-related commands."""
        parts = args.split(maxsplit=1)
        subcmd = parts[0].lower() if parts else ""

        if subcmd == "list":
            self.output.print_info("MCP servers (placeholder)")

        elif subcmd == "add":
            self.output.print_info("Use ~/.geoffrey/mcp.json to configure MCP servers")

        else:
            self.output.print_info("MCP commands: list, add")


async def create_repl(
    provider: str = "kimi",
    model_name: Optional[str] = None,
    config_path: Optional[Path] = None,
) -> REPL:
    """
    Create and configure a REPL instance.

    Args:
        provider: Model provider name (kimi, deepseek, qwen, openai)
        model_name: Specific model to use
        config_path: Path to config file
    """
    # Get model config
    model_config = ModelConfig(
        model_name=model_name or "moonshot-v1-8k",
    )

    # Create model
    registry = get_registry()
    model = registry.create(provider, model_config)

    # Create REPL
    repl = REPL(model=model)

    return repl


async def run_repl(
    provider: str = "kimi",
    model_name: Optional[str] = None,
):
    """Run the REPL with specified provider."""
    repl = await create_repl(provider=provider, model_name=model_name)
    await repl.run()
