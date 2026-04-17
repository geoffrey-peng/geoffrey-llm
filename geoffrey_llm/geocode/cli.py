"""CLI entry point for geocode."""

import argparse
import asyncio
import sys
from pathlib import Path


def main():
    """Main entry point for geocode CLI."""
    parser = argparse.ArgumentParser(
        description="geocode - Claude Code-like coding assistant",
        prog="geocode",
    )

    parser.add_argument(
        "--provider",
        choices=["kimi", "deepseek", "qwen", "openai"],
        default="kimi",
        help="Model provider to use (default: kimi)",
    )
    parser.add_argument(
        "--model",
        help="Model name (provider-specific)",
    )
    parser.add_argument(
        "--new",
        action="store_true",
        help="Start a new session",
    )
    parser.add_argument(
        "--resume",
        metavar="SESSION_ID",
        help="Resume an existing session",
    )
    parser.add_argument(
        "--sessions",
        action="store_true",
        help="List all sessions",
    )

    args = parser.parse_args()

    # Run the async main
    try:
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        print("\nGoodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


async def async_main(args):
    """Async main function."""
    from geoffrey_llm.geocode.cmd.repl import REPL, run_repl
    from geoffrey_llm.geocode.models.base import get_registry, ModelConfig

    if args.sessions:
        # List sessions
        from geoffrey_llm.geocode.session.manager import SessionManager
        manager = SessionManager()
        sessions = manager.list()

        if not sessions:
            print("No sessions found")
        else:
            print(f"Found {len(sessions)} session(s):\n")
            for s in sessions:
                print(f"  {s.id}")
                print(f"    Created: {s.created_at}")
                print(f"    Last active: {s.last_active}")
                if s.project_path:
                    print(f"    Project: {s.project_path}")
                print()
        return

    # Get model config
    model_config = ModelConfig(
        model_name=args.model or get_default_model(args.provider),
    )

    # Create and run REPL
    registry = get_registry()
    model = registry.create(args.provider, model_config)
    repl = REPL(model=model)

    await repl.run()


def get_default_model(provider: str) -> str:
    """Get default model name for a provider."""
    defaults = {
        "kimi": "moonshot-v1-8k",
        "deepseek": "deepseek-chat",
        "qwen": "qwen-plus",
        "openai": "gpt-3.5-turbo",
    }
    return defaults.get(provider, "gpt-3.5-turbo")


if __name__ == "__main__":
    main()
