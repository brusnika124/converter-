from __future__ import annotations

from pathlib import Path

from meter_converter.errors import UnsupportedFormatError
from meter_converter.parsers.base import ProfileParser
from meter_converter.parsers.html_parser import HtmlProfileParser
from meter_converter.parsers.txt_parser import TxtProfileParser
from meter_converter.parsers.xml_parser import XmlProfileParser
from meter_converter.parsers.xlsx_parser import XlsxProfileParser


class ParserRegistry:
    def __init__(self) -> None:
        self._parsers: dict[str, ProfileParser] = {
            ".html": HtmlProfileParser(),
            ".txt": TxtProfileParser(),
            ".xlsx": XlsxProfileParser(),
            ".xml": XmlProfileParser(),
        }

    def for_path(self, path: Path) -> ProfileParser:
        try:
            return self._parsers[path.suffix.lower()]
        except KeyError as exc:
            raise UnsupportedFormatError(
                f"Неподдерживаемый формат: {path.suffix or 'без расширения'}"
            ) from exc
