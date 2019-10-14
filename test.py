#!/usr/bin/env python3

import asyncio

from prompt_toolkit.application import Application
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.eventloop import use_asyncio_event_loop
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import Float, FloatContainer, VSplit, HSplit, Window, WindowAlign
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Frame, TextArea

# Tell prompt_toolkit to use asyncio for the event loop.
use_asyncio_event_loop()

_BORDER_VERTICAL = '│'
_BORDER_HORIZONTAL = '─'
_BORDER_LEFT_BOTTOM = '└'
_BORDER_RIGHT_BOTTOM = '┘'
_BORDER_LEFT_TOP = '┌'
_BORDER_RIGHT_TOP = '┐'

_FOCUSED_BORDER_TITLEBAR = '┃'
_FOCUSED_BORDER_VERTICAL = '┃'
_FOCUSED_BORDER_HORIZONTAL = '━'
_FOCUSED_BORDER_LEFT_TOP = '┏'
_FOCUSED_BORDER_RIGHT_TOP = '┓'
_FOCUSED_BORDER_LEFT_BOTTOM = '┗'
_FOCUSED_BORDER_RIGHT_BOTTOM = '┛'

style = Style.from_dict({
    'titlebar-logo': 'bg:#888888 #222222 bold',
    'titlebar': 'bg:#888888 #222222',
    'border': '#888888',
})

DRUID_COMMANDS = {
    "bootloader": "Reboot into bootloader",
    "clear": "Clear the saved user script",
    "first": "Set First as the current script and reboot",
    "help": "Show help",
    "identity": "Show crow's serial number",
    "kill": "Restart the Lua environment",
    "print": "Print the current user script",
    "quit": "Quit druid",
    "reset": "Reboot crow",
    "run": "Send a file to crow and run it",
    "upload": "Send a file to crow, store and run it",
    "version": "Print the current firmware version"
}

druid_completer = WordCompleter(words=DRUID_COMMANDS.keys(), ignore_case=True,
                                meta_dict=DRUID_COMMANDS)

kb = KeyBindings()

@kb.add('c-q')
def exit_(event):
    """
    Pressing Ctrl-Q will exit the user interface.

    Setting a return value means: quit the event loop that drives the user
    interface and return this value from the `Application.run()` call.
    """
    event.app.exit()


druid_intro = "//// druid. q to quit. h for help\n\n"
druid_help = """
 h            this menu
 r            runs 'sketch.lua'
 u            uploads 'sketch.lua'
 r <filename> run <filename>
 u <filename> upload <filename>
 p            print current userscript
 q            quit

"""

captures = VSplit([
    TextArea(text="capture1 contents", style='class:capture-field', height=2),
    TextArea(text="capture2 contents", style='class:capture-field', height=2)
    ], padding=1, padding_char=_BORDER_VERTICAL, padding_style='class:border')
output = TextArea(style='class:output-field', text="output contents")
statusbar = VSplit([
    Window(height=1, content=FormattedTextControl(text="Input 1: -0.38764823  Input 2: 4.257895"), style='class:titlebar'),
    Window(height=1, width=4, style='class:titlebar', content=FormattedTextControl(text='////'), align=WindowAlign.RIGHT),
    Window(height=1, width=12, style='class:titlebar-logo', content=FormattedTextControl(text='druid v0.2.0'), align=WindowAlign.RIGHT),
    Window(height=1, width=1, style='class:titlebar', content=FormattedTextControl(text=' '), align=WindowAlign.RIGHT),
    ], padding=1, padding_style="class:titlebar")
input = TextArea(height=1, prompt='> ', completer=druid_completer, style='class:input-field', multiline=False, wrap_lines=False)
container = FloatContainer(
    content=HSplit([
        output,
        input,
        statusbar,
    ]),
    floats=[
        Float(content=CompletionsMenu(max_height=16, scroll_offset=1),
              xcursor=True, ycursor=True)
    ])

app = Application(
    layout=Layout(container, focused_element=input),
    key_bindings=kb,
    mouse_support=True,
    full_screen=True,
    style=style,
)

# Run the application, and wait for it to finish.
asyncio.get_event_loop().run_until_complete(
    app.run_async().to_asyncio_future())
