""" Command-line interface for druid """

import sys
import time

import click

from druid.crowlib import Crow
from druid import repl as druid_repl

@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option()
def cli(ctx):
    """ Terminal interface for crow """
    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)

@cli.command(short_help="Download a file from crow")
def download():
    """
    Download a file from crow and print it to stdout
    """
    crow = Crow()
    try:
        click.echo(crow.print())
        crow.close()
    except (FileNotFoundError, ConnectionError) as err:
        sys.exit(err)

@cli.command(short_help="Upload a file to crow")
@click.argument("filename", type=click.Path(exists=True))
def upload(filename):
    """
    Upload a file to crow.
    FILENAME is the path to the Lua file to upload
    """
    crow = Crow()
    try:
        with open(filename) as script_file:
            crow.upload(script_file.read())
    except (FileNotFoundError, ConnectionError) as err:
        sys.exit(err)

    # Print logging from crow in case any errors occured during upload
    click.echo(crow.read())
    click.echo("File uploaded")
    # Wait for new script to be ready
    time.sleep(0.5)
    # Print the uploaded script
    click.echo(crow.print())
    crow.close()

@cli.command()
@click.argument("filename", type=click.Path(exists=True), required=False)
def repl(filename):
    """ Start interactive terminal """
    druid_repl.main(filename)
