#!/usr/bin/env python

# TODO: proper logging configuration
import logging

from cleo import Application as BaseApplication
from clikit.api.args.format.argument import Argument
from clikit.api.args.format.option import Option
from clikit.api.args.raw_args import RawArgs
from clikit.api.config.application_config import ApplicationConfig as BaseApplicationConfig
from clikit.api.event import PRE_HANDLE, PRE_RESOLVE, EventDispatcher, PreHandleEvent, PreResolveEvent
from clikit.api.io import IO, Input, InputStream, Output, OutputStream
from clikit.api.io.flags import DEBUG, VERBOSE, VERY_VERBOSE
from clikit.api.resolver import ResolvedCommand
from clikit.config import DefaultApplicationConfig
from clikit.formatter import AnsiFormatter, DefaultStyleSet, PlainFormatter
from clikit.handler.help import HelpTextHandler
from clikit.io import ConsoleIO
from clikit.io.input_stream import StandardInputStream
from clikit.io.output_stream import ErrorOutputStream, StandardOutputStream
from clikit.resolver.default_resolver import DefaultResolver
from clikit.resolver.help_resolver import HelpResolver
from clikit.ui.components import NameVersion

from krawl import __version__
from krawl.cli.command.fetch import FetchCommand
from krawl.cli.command.list import ListCommand

logging.basicConfig(level=logging.DEBUG)


class Application(BaseApplication):

    def __init__(self):
        config = ApplicationConfig()
        super().__init__(config=config)

        # add commands
        self.add(FetchCommand())
        self.add(ListCommand())


class ApplicationConfig(DefaultApplicationConfig):

    def __init__(self):
        super().__init__(name="Krawler", version=__version__)

    def configure(self):
        self.set_io_factory(self.create_io)
        self.add_event_listener(PRE_RESOLVE, self.resolve_help_command)
        self.add_event_listener(PRE_HANDLE, self.print_version)

        self.add_option("help", "h", Option.NO_VALUE, "Display this help message")
        self.add_option("quiet", "q", Option.NO_VALUE, "Do not output any message")
        self.add_option(
            "verbose",
            "v",
            Option.OPTIONAL_VALUE,
            "Increase the verbosity of messages: "
            '"-v" for normal output, '
            '"-vv" for more verbose output '
            'and "-vvv" for debug',
        )
        self.add_option("version", "V", Option.NO_VALUE, "Display this application version")
        self.add_option("ansi", None, Option.NO_VALUE, "Force ANSI output")
        self.add_option("no-ansi", None, Option.NO_VALUE, "Disable ANSI output")

        with self.command("help") as c:
            c.default()
            c.set_description("Display the manual of a command")
            c.add_argument("command", Argument.OPTIONAL | Argument.MULTI_VALUED, "The command name")
            c.set_handler(HelpTextHandler(HelpResolver()))

    def resolve_help_command(self, event, event_name,
                             dispatcher):  # type: (PreResolveEvent, str, EventDispatcher) -> None
        args = event.raw_args
        application = event.application

        if args.has_option_token("-h") or args.has_option_token("--help"):
            command = application.get_command("help")

            # Enable lenient parsing
            parsed_args = command.parse(args, True)

            event.set_resolved_command(ResolvedCommand(command, parsed_args))
            event.stop_propagation()

    def print_version(self, event, event_name, dispatcher):  # type: (PreHandleEvent, str, EventDispatcher) -> None
        if event.args.is_option_set("version"):
            version = NameVersion(event.command.application.config)
            version.render(event.io)

            event.handled(True)


def main():
    application = Application()
    application.run()


if __name__ == '__main__':
    main()
