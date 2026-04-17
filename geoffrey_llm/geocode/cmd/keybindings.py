"""Keybinding handlers for REPL."""

from typing import Callable, Optional

try:
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.keys import Keys
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent
    HAS_PROMPT_TOOLKIT = True
except ImportError:
    HAS_PROMPT_TOOLKIT = False


class Keybindings:
    """
    Keybinding handlers for REPL.

    Handles special key combinations like Ctrl-C for interrupt.
    """

    def __init__(self):
        self._interrupt_callback: Optional[Callable] = None
        self._bindings = self._create_bindings()

    def _create_bindings(self):
        """Create prompt_toolkit key bindings."""
        if not HAS_PROMPT_TOOLKIT:
            return None

        kb = KeyBindings()

        @kb.add(Keys.ControlC)
        def handle_ctrl_c(event: KeyPressEvent):
            """Handle Ctrl-C for interrupt."""
            event.app.exit(exception=KeyboardInterrupt, style="class:aborting")

        @kb.add(Keys.ControlD)
        def handle_ctrl_d(event: KeyPressEvent):
            """Handle Ctrl-D for exit."""
            event.app.exit(result=None)

        return kb

    def set_interrupt_callback(self, callback: Callable):
        """Set callback for interrupt (Ctrl-C)."""
        self._interrupt_callback = callback

    def get_bindings(self):
        """Get the key bindings for prompt_toolkit."""
        return self._bindings

    def add_binding(self, key: str, handler: Callable):
        """Add a custom binding."""
        if self._bindings and HAS_PROMPT_TOOLKIT:
            self._bindings.add(key)(handler)
