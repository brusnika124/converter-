from datetime import datetime

import pytest

from meter_converter.domain import DataType
from meter_converter.parsers.xml_parser import XmlProfileParser


XML_TEMPLATE = '''<?xml version="1.0"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
          xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
  <Worksheet ss:Name="Лист1">
    <Table>
      <Row><Cell><Data ss:Type="String">Время</Data></Cell><Cell><Data ss:Type="String">Значение</Data></Cell></Row>
      <Row><Cell><Data ss:Type="String">01.09.26 01:00:00</Data></Cell><Cell><Data ss:Type="String">2717,000</Data></Cell></Row>
      <Row><Cell><Data ss:Type="String">01.09.26 00:30:00</Data></Cell><Cell><Data ss:Type="String">2000,000</Data></Cell></Row>
      <Row><Cell><Data ss:Type="String">01.09.26 00:00:00</Data></Cell><Cell><Data ss:Type="String">1500,000</Data></Cell></Row>
    </Table>
  </Worksheet>
</Workbook>
'''


def test_xml_parser_reverses_timeline_and_converts_watts_to_kw(tmp_path):
    path = tmp_path / "profile.xml"
    path.write_text(XML_TEMPLATE, encoding="utf-8")

    profile = XmlProfileParser().parse(path)

    assert profile.data_type == DataType.P_PLUS
    assert profile.interval.minutes == 30
    assert profile.value_column == "P+"
    assert profile.value_column_index == 1
    assert profile.frame["_timestamp"].tolist() == [
        datetime(2026, 9, 1, 0, 0),
        datetime(2026, 9, 1, 0, 30),
        datetime(2026, 9, 1, 1, 0),
    ]
    assert profile.frame["P+"].tolist() == pytest.approx([1.5, 2.0, 2.717])


def test_xml_parser_keeps_source_time_column_in_output(tmp_path):
    path = tmp_path / "profile.xml"
    path.write_text(XML_TEMPLATE, encoding="utf-8")

    profile = XmlProfileParser().parse(path)

    assert profile.frame["Время"].tolist()[0] == "01.09.26 00:00:00"


def test_registry_supports_xml():
    from pathlib import Path
    from meter_converter.parsers.registry import ParserRegistry

    assert isinstance(ParserRegistry().for_path(Path("profile.xml")), XmlProfileParser)
