from cleo import Command


class CleoTestCommandBase(Command):

    def __init__(self):
        super().__init__()
        self._engine = None
        # self.add_style('warning', fg='yellow', options=['bold'])
