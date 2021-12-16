from cleo import Command


class KrawlCommand(Command):

    def option_int(self, key, default=None, min=None, max=None):
        value = self.option(key)
        if value is None:
            return default
        if isinstance(value, str):
            value = value.strip()
            if not value.isdigit():
                raise ValueError(f"'{key}' must be a number, got this instead: {value}")
            value = int(value)
        if not isinstance(value, int):
            raise ValueError()
        if min is not None and value < min:
            raise ValueError(f"{key} must be greater than {min}")
        if max is not None and value > max:
            raise ValueError(f"{key} must be lower than {max}")
        return value
