class ConverterError(Exception):
    """Base application error suitable for showing to the user."""


class UnsupportedFormatError(ConverterError):
    pass


class InvalidProfileError(ConverterError):
    pass
