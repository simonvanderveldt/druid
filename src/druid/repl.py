""" Druid REPL """
import asyncio
import logging.config
import os
import sys

from prompt_toolkit.eventloop.defaults import use_asyncio_event_loop
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.application import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.document import Document
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import (
    VSplit, HSplit,
    Window, WindowAlign,
)
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.screen import Char
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.layout.controls import FormattedTextControl

from druid import crowlib


# monkey patch to fix https://github.com/monome/druid/issues/8
Char.display_mappings['\t'] = '  '

DRUID_HELP = """
 h            this menu
 r            runs 'sketch.lua'
 u            uploads 'sketch.lua'
 r <filename> run <filename>
 u <filename> upload <filename>
 p            print current userscript
 q            quit

"""


class DruidRepl():
    """ Druid REPL, the main thing, contains all state as well as the REPL UI """
    def __init__(self):
        self.crow = None
        self.is_connected = None
        self.capture1 = TextArea(style='class:capture-field', height=2)
        self.capture2 = TextArea(style='class:capture-field', height=2)
        self.output_field = TextArea(style='class:output-field',
                                     text="//// druid. q to quit. h for help\n\n")
        self.input_field = TextArea(height=1, prompt='> ', multiline=False, wrap_lines=False,
                                    accept_handler=self._input_handler, style='class:input-field')
        self.statusbar = Window(height=1, char='/', style='class:line',
                                content=FormattedTextControl(text='druid////'),
                                align=WindowAlign.RIGHT)

    def druidparser(self, writer, cmd):
        """
        Parser for druid commands
        Translates single letter commands into actions performed against crow
        """
        parts = cmd.split(maxsplit=1)

        # No command passed, skip
        if len(parts) == 0:
            return

        command = parts[0]
        # Quit
        if command == "q":
            get_app().exit()
        # Print script
        elif command == "p":
            writer(bytes("^^p", 'utf-8'))
        # Show help
        elif command == "h":
            self.myprint(DRUID_HELP)
        # Run a script
        elif command == "r":
            if len(parts) == 2 and os.path.isfile(parts[1]):
                crowlib.execute(writer, self.myprint, parts[1])
            else:
                self.myprint("usage: r <path to file to run>")
        # Upload a script
        elif command == "u":
            if len(parts) == 2 and os.path.isfile(parts[1]):
                crowlib.upload(writer, self.myprint, parts[1])
            else:
                self.myprint("usage: u <path to file to upload>")
        # If no known command was received send the input to crow
        else:
            writer(bytes(cmd + "\r\n", 'utf-8'))

    def crowparser(self, text):
        """
        Parser for crow messages
        Separetes stream/change messages from other messages
        """
        if "^^" in text:
            cmds = text.split('^^')
            for cmd in cmds:
                t3 = cmd.rstrip().partition('(')
                x = t3[0]
                args = t3[2].rstrip(')').partition(',')
                if x in ("stream", "change"):
                    dest = self.capture1
                    if args[0] == "2":
                        dest = self.capture2
                    self._print(dest, ('\ninput['+args[0]+'] = '+args[2]+'\n'))
                elif len(cmd) > 0:
                    self.myprint('^^'+cmd+'\n')
        elif len(text) > 0:
            self.myprint(text+'\n')

    def cwrite(self, xs):
        try:
            if len(xs)%64 == 0:
                # Hack to handle osx/win serial port crash
                xs = xs + ('\n').encode('ascii')
            self.crow.write(xs)
        except:
            self.crowreconnect()

    def _input_handler(self, buffer):
        text = buffer.text
        self.myprint(f"\n> {text}\n")
        self.druidparser(self.cwrite, text)

    async def shell(self):
        kb = KeyBindings()

        @kb.add('c-c', eager=True)
        @kb.add('c-q', eager=True)
        def _(event):
            event.app.exit()

        style = Style([
            ('capture-field', '#747369'),
            ('output-field', '#d3d0c8'),
            ('input-field', '#f2f0ec'),
            ('line', '#747369'),
        ])

        captures = VSplit([self.capture1, self.capture2])
        container = HSplit([
            captures,
            self.output_field,
            self.statusbar,
            self.input_field])

        application = Application(
            layout=Layout(container, focused_element=self.input_field),
            key_bindings=kb,
            style=style,
            mouse_support=True,
            full_screen=True,
        )
        await application.run_async()


    def _print(self, field, st):
        s = field.text + st.replace('\r', '')
        field.buffer.document = Document(text=s, cursor_position=len(s))

    def myprint(self, st):
        self._print(self.output_field, st)

    def crowreconnect(self, errmsg=None):
        try:
            self.crow = crowlib.connect()
            self.myprint(" <crow connected>\n")
            self.is_connected = True
        except ValueError:
            if errmsg is not None:
                self.myprint(" <{}>\n".format(errmsg))
            elif self.is_connected:
                self.myprint(" <crow disconnected>\n")
                self.is_connected = False

    async def printer(self):
        while True:
            sleeptime = 0.001
            try:
                r = self.crow.read(10000)
                if len(r) > 0:
                    lines = r.decode('ascii').split('\n\r')
                    for line in lines:
                        crowparser(line)
            except:
                sleeptime = 0.1
                self.crowreconnect()
            await asyncio.sleep(sleeptime)

    def exit(self):
        if self.is_connected:
            self.crow.close()


def main():
    logging.config.dictConfig({
        'version': 1,
        'formatters': {
            'detailed': {
                'class': 'logging.Formatter',
                'format': '%(asctime)s %(name)-15s %(levelname)-8s'
                          '%(processName)-10s %(message)s'
            },
        },
        'handlers': {
            'file': {
                'class': 'logging.FileHandler',
                'filename': 'druid.log',
                'mode': 'w',
                'formatter': 'detailed',
            },
        },
        'loggers': {
            'crowlib': {
                'handlers': ['file'],
            },
        },
        'root': {
            'level': 'DEBUG',
            'handlers': [],
        },
    })

    repl = DruidRepl()

    repl.crowreconnect(errmsg="crow disconnected")

    loop = asyncio.get_event_loop()

    use_asyncio_event_loop()

    with patch_stdout():
        background_task = asyncio.gather(repl.printer(), return_exceptions=True)
        loop.run_until_complete(repl.shell())
        background_task.cancel()

    repl.exit()
    sys.exit()
