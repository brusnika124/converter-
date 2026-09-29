
meter_converter/
├── bootstrap.py                 # Composition root / запуск приложения
├── domain.py                    # Модели и enum без UI
├── months.py                    # Названия месяцев
├── errors.py                    # Ошибки приложения
├── parsers/
│   ├── base.py                  # Контракт ProfileParser
│   ├── registry.py              # Выбор парсера по расширению
│   ├── html_parser.py           # HTML -> ParsedProfile
│   ├── txt_parser.py            # TXT -> ParsedProfile
│   └── xlsx_parser.py           # XLSX -> ParsedProfile
├── services/
│   ├── application.py           # Сценарий конвертации
│   ├── reference_catalog.py     # Справочники по месяцу/году
│   ├── timeline_validator.py    # Проверка временной линии и выбросов
│   ├── legacy_partition.py      # Позиционный fallback без timestamp
│   ├── profile_cleaner.py       # Compatibility alias старого API
│   ├── kt_calculator.py         # Формулы P+/A+ и КТ
│   ├── excel_exporter.py        # Формирование итогового XLSX
│   └── output_path.py           # профиль.xlsx, профиль1.xlsx, ...
└── ui/
    ├── main_window.py           # Только Tkinter/UI-события
    ├── theme.py                 # Цвета
    └── drawing.py               # UI drawing helpers
```
