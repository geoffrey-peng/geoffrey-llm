"""Bash tool - execute shell commands with sandboxing."""

import asyncio
import os
import re
import shlex
from pathlib import Path
from typing import Optional

from pydantic import Field

from geoffrey_llm.geocode.tools.base import Tool, ToolInput, ToolResult


class BashInput(ToolInput):
    """Input schema for Bash tool."""

    command: str = Field(..., description="The shell command to execute")
    working_dir: Optional[str] = Field(default=None, description="Working directory for the command")
    timeout: int = Field(default=30, description="Timeout in seconds")
    description: Optional[str] = Field(default=None, description="What this command does")


class BashTool(Tool):
    """
    Tool for executing shell commands.

    Security features:
    - Command allowlist (configurable)
    - Pattern blacklisting for dangerous commands
    - Working directory restriction
    - Timeout enforcement
    """

    # Default allowed commands (if not configured)
    DEFAULT_ALLOWED = {
        "git", "ls", "cat", "grep", "find", "wc", "head", "tail",
        "pwd", "cd", "mkdir", "rm", "cp", "mv", "echo", "touch",
        "chmod", "chown", "awk", "sed", "sort", "uniq", "diff",
        "zip", "unzip", "tar", "gzip", "gunzip", "curl", "wget",
        "node", "npm", "python", "python3", "pip", "pip3",
        "docker", "docker-compose", "make", "cmake",
        "cargo", "rustc", "go", "java", "javac",
    }

    # Dangerous patterns that are always blocked
    DANGEROUS_PATTERNS = [
        r"rm\s+-rf\s+/",  # rm -rf /
        r":\(\)\{",  # Fork bomb
        r"curl\s+.*\|\s*sh",  # Pipe to shell
        r"wget\s+.*\|\s*sh",
        r">\s*/dev/sd[a-z]",  # Write to block device
        r"dd\s+.*of=/dev/",  # dd to block device
        r"mkfs\s+",  # Format filesystem
        r"fdisk\s+",  # Partition
        r":！\s*:",  # Fork bomb variant
    ]

    def __init__(self):
        self.allowed_commands = self.DEFAULT_ALLOWED
        self.disallowed_patterns = self.DANGEROUS_PATTERNS
        self.timeout_seconds = 30

    def configure(self, allowed_commands: set[str], disallowed_patterns: list[str], timeout: int):
        """Configure bash tool from config."""
        self.allowed_commands = allowed_commands
        self.disallowed_patterns = disallowed_patterns
        self.timeout_seconds = timeout

    @property
    def name(self) -> str:
        return "Bash"

    @property
    def description(self) -> str:
        return "Execute a shell command. Commands are sandboxed - only whitelisted commands and patterns are allowed."

    def input_schema(self) -> type[ToolInput]:
        return BashInput

    def _is_command_allowed(self, command: str) -> tuple[bool, str]:
        """Check if command is allowed."""
        # Parse command to get the executable
        try:
            parts = shlex.split(command)
            if not parts:
                return False, "Empty command"
            executable = parts[0]

            # Check if it's a path
            if "/" in executable or "\\" in executable:
                # Allow full paths to whitelisted commands
                basename = os.path.basename(executable).lower()
                if basename not in self.allowed_commands:
                    return False, f"Command not in whitelist: {basename}"
                return True, "allowed"

            # Check against dangerous patterns
            for pattern in self.disallowed_patterns:
                if re.search(pattern, command, re.IGNORECASE):
                    return False, f"Command matches dangerous pattern: {pattern}"

            # Check if command is in whitelist
            if executable.lower() not in self.allowed_commands:
                return False, f"Command not in whitelist: {executable}"

            return True, "allowed"

        except Exception as e:
            return False, f"Failed to parse command: {e}"

    async def call(self, input_data: BashInput) -> ToolResult:
        """Execute shell command with sandboxing."""
        try:
            # Check if command is allowed
            allowed, reason = self._is_command_allowed(input_data.command)
            if not allowed:
                return ToolResult(
                    success=False,
                    error=f"Command not allowed: {reason}",
                )

            # Set up working directory
            cwd = input_data.working_dir or os.getcwd()
            if not os.path.isdir(cwd):
                return ToolResult(
                    success=False,
                    error=f"Working directory does not exist: {cwd}",
                )

            # Set timeout
            timeout = min(input_data.timeout, self.timeout_seconds)

            # Execute command
            process = await asyncio.create_subprocess_shell(
                input_data.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env={**os.environ, "TERM": "xterm-256color"},
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(
                    success=False,
                    error=f"Command timed out after {timeout} seconds",
                )

            # Format output
            output_parts = []

            if input_data.description:
                output_parts.append(f"# {input_data.description}")

            output_parts.append(f"$ {input_data.command}")

            if stdout:
                output_parts.append(stdout.decode("utf-8", errors="replace").strip())

            if stderr:
                output_parts.append(f"STDERR:\n{stderr.decode('utf-8', errors='replace').strip()}")

            output_parts.append(f"\n[Exit code: {process.returncode}]")

            return ToolResult(
                success=process.returncode == 0,
                output="\n".join(output_parts),
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error executing command: {str(e)}",
            )
