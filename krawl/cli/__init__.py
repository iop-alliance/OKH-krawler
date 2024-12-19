#!/usr/bin/env python

from __future__ import annotations

from cleo import Application as BaseApplication
from clikit.api.args.format.argument import Argument
from clikit.api.args.format.option import Option
from clikit.api.event import PRE_HANDLE, PRE_RESOLVE
from clikit.api.formatter import Formatter
from clikit.api.formatter.style_set import StyleSet
from clikit.api.io import Input, Output
from clikit.api.io.flags import DEBUG, VERBOSE, VERY_VERBOSE
from clikit.api.io.input_stream import InputStream
from clikit.api.io.output_stream import OutputStream
from clikit.config import DefaultApplicationConfig
from clikit.formatter import AnsiFormatter, PlainFormatter
from clikit.handler.help import HelpTextHandler
from clikit.io.console_io import ConsoleIO
from clikit.io.input_stream import StandardInputStream
from clikit.io.output_stream import ErrorOutputStream, StandardOutputStream
from clikit.resolver.help_resolver import HelpResolver

from krawl import __version__
from krawl.cli.command.fetch import FetchCommand
from krawl.cli.command.list import ListCommand
from krawl.log import configure_logger


class Application(BaseApplication):

    def __init__(self):
        config = ApplicationConfig()
        super().__init__(config=config)

        # add commands
        self.add(FetchCommand())
        self.add(ListCommand())


def create_formatter(output_stream: OutputStream, style_set: StyleSet) -> Formatter:
    if output_stream.supports_ansi():
        return AnsiFormatter(style_set)
    return PlainFormatter(style_set)


class ApplicationConfig(DefaultApplicationConfig):

    def __init__(self):
        super().__init__(name="krawl", version=__version__)

    def configure(self):
        self.set_io_factory(self.create_io)
        self.add_event_listener(PRE_RESOLVE, self.resolve_help_command)
        self.add_event_listener(PRE_HANDLE, self.print_version)

        self.add_option("help", "h", Option.NO_VALUE, "Display this help message")
        self.add_option(
            "verbose",
            "v",
            Option.NO_VALUE,
            "Increase the verbosity of messages: '-v' for warnings, '-vv' for info and '-vvv' for debug",
        )
        self.add_option("version", None, Option.NO_VALUE, "Display this application version")
        self.add_option("no-ansi", None, Option.NO_VALUE, "Disable ANSI output")
        self.add_option("config", "c", Option.REQUIRED_VALUE, "Path to configuration file.")

        with self.command("help") as c:
            c.default()
            c.set_description("Display the manual of a command")
            c.add_argument("command", Argument.OPTIONAL | Argument.MULTI_VALUED, "The command name")
            c.set_handler(HelpTextHandler(HelpResolver()))

    def create_io(self,
                  application,
                  args,
                  input_stream: InputStream = None,
                  output_stream: OutputStream = None,
                  error_stream: OutputStream = None) -> ConsoleIO:
        if input_stream is None:
            input_stream = StandardInputStream()
        if output_stream is None:
            output_stream = StandardOutputStream()
        if error_stream is None:
            error_stream = ErrorOutputStream()

        style_set = application.config.style_set

        if args.has_option_token("--no-ansi"):
            output_formatter = error_formatter = PlainFormatter(style_set)
        else:
            output_formatter = create_formatter(output_stream, style_set)
            error_formatter = create_formatter(error_stream, style_set)

        io = self.io_class(
            Input(input_stream),
            Output(output_stream, output_formatter),
            Output(error_stream, error_formatter),
        )

        colored_format = "<info>%(asctime)s</info> | <c1>%(levelname)-7s</c1> | <c2>%(name)s</c2> | %(message)s"
        if args.has_option_token("-vvv"):
            io.set_verbosity(DEBUG)
            log_level = "debug"
        elif args.has_option_token("-vv"):
            io.set_verbosity(VERY_VERBOSE)
            log_level = "info"
        elif args.has_option_token("-v"):
            io.set_verbosity(VERBOSE)
            log_level = "warning"
        else:
            log_level = "error"
        configure_logger(log_level, colored_format, io.output, io.error_output)

        return io


def main():
    application = Application()
    application.run()


if __name__ == '__main__':
    main()
