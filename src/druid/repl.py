""" Druid REPL """
# pylint: disable=C0103
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
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.screen import Char
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Label, TextArea

from druid import crowlib

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class PassThroughHandler(logging.Handler):
    """ Log handler that appends the log messages it receives to another object """
    def __init__(self, out, level=logging.INFO):
        super().__init__(level)
        self.out = out

    def emit(self, record):
        # self.out.text = record.getMessage()
        # raise SystemExit(1)
        # append(record.getMessage(), self.out)
        new_text = self.out.text + record.getMessage().replace('\r', '')
        self.out.buffer.document = Document(text=new_text, cursor_position=len(new_text))


# monkey patch to fix https://github.com/monome/druid/issues/8
Char.display_mappings['\t'] = '  '

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

def druidparser(writer, cmd):
    """
    Parser for druid commands
    Translates single letter commands into actions performed against crow
    """
    global logger
    parts = cmd.split(maxsplit=1)
    if len(parts) == 0:
        return
    c = parts[0]
    if c == "q":
        raise ValueError("bye.")
    if c == "r":
        if len(parts) == 1:
            crowlib.execute(writer, myprint, "./sketch.lua")
        elif len(parts) == 2 and os.path.isfile(parts[1]):
            crowlib.execute(writer, myprint, parts[1])
        else:
            writer(bytes(cmd + "\r\n", 'utf-8'))
    elif c == "u":
        if len(parts) == 1:
            crowlib.upload(writer, myprint, "./sketch.lua")
        elif len(parts) == 2 and os.path.isfile(parts[1]):
            crowlib.upload(writer, myprint, parts[1])
        else:
            writer(bytes(cmd + "\r\n", 'utf-8'))
    elif c == "p":
        writer(bytes("^^p", 'utf-8'))
    elif c == "h":
        logger.info("TEST")
        myprint(druid_help)
    else:
        writer(bytes(cmd + "\r\n", 'utf-8'))

def crowparser(text):
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
                dest = capture1
                if args[0] == "2":
                    dest = capture2
                _print(dest, ('\ninput['+args[0]+'] = '+args[2]+'\n'))
            elif len(cmd) > 0:
                myprint('^^'+cmd+'\n')
    elif len(text) > 0:
        myprint(text+'\n')

capture1 = TextArea(style='class:capture-field', height=2)
capture2 = TextArea(style='class:capture-field', height=2)
captures = VSplit([capture1, capture2])
output_field = TextArea(style='class:output-field', text=druid_intro)
status = Label(text="")
statusbar = VSplit([
    Label(text="Status: "),
    status,
    Window(height=1, char='/', style='class:line', content=FormattedTextControl(text='druid////'),
           align=WindowAlign.RIGHT)])
input_field = TextArea(height=1, prompt='> ', multiline=False, wrap_lines=False,
                       style='class:input-field')
container = HSplit([
    captures,
    output_field,
    statusbar,
    input_field])

crow = None

logging.getLogger("druid").addHandler(PassThroughHandler(out=output_field))
logger.addHandler(PassThroughHandler(out=output_field))

print(logger.handlers)
logger.info("blabli")

async def shell():
    global crow

    def cwrite(xs):
        global crow
        try:
            crow.write(xs)
        except:
            crowreconnect()

    def accept(buff):
        try:
            myprint('\n> '+input_field.text+'\n')
            druidparser(cwrite, input_field.text)
        except ValueError as err:
            print(err)
            get_app().exit()

    input_field.accept_handler = accept

    kb = KeyBindings()

    @kb.add('c-c', eager=True)
    @kb.add('c-q', eager=True)
    def _(event):
        event.app.exit()

    @kb.add('c-a', eager=True)
    def _(event):
        logger.info("This is a test")

    style = Style([
        ('capture-field', '#747369'),
        ('output-field', '#d3d0c8'),
        ('input-field', '#f2f0ec'),
        ('line', '#747369'),
    ])

    application = Application(
        layout=Layout(container, focused_element=input_field),
        key_bindings=kb,
        style=style,
        mouse_support=True,
        full_screen=True,
    )
    result = await application.run_async()


def _print(field, st):
    s = field.text + st.replace('\r', '')
    field.buffer.document = Document(text=s, cursor_position=len(s))

def myprint(st):
    _print(output_field, st)

def crowreconnect():
    global crow
    try:
        crow = crowlib.connect()
        myprint(" <online!>\n")
    except ValueError:
        myprint(" <lost connection>\n")

async def printer():
    global crow
    while True:
        sleeptime = 0.001
        try:
            r = crow.read(10000)
            if len(r) > 0:
                lines = r.decode('ascii').split('\n\r')
                for line in lines:
                    crowparser(line)
        except:
            sleeptime = 1.0
            crowreconnect()
        await asyncio.sleep(sleeptime)


def main(script=None):
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

    global crow
    try:
        crow = crowlib.connect()
    except OSError as err:
        status.text = "disconnected"
        print(err)
        # sys.exit(1)

    # run script passed from command line
    if script:
        crowlib.execute(crow.write, myprint, script)

    loop = asyncio.get_event_loop()

    use_asyncio_event_loop()

    with patch_stdout():
        background_task = asyncio.gather(printer(), return_exceptions=True)
        loop.run_until_complete(shell())
        background_task.cancel()
        loop.run_until_complete(background_task)

    crow.close()
    sys.exit()
