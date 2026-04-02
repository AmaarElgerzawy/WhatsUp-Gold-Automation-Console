from __future__ import annotations

import json


class BulkTemplateRepository:
    def __init__(self, template_file, default_encoding: str) -> None:
        self._template_file = template_file
        self._default_encoding = default_encoding

    def load_templates(self):
        return json.loads(self._template_file.read_text(encoding=self._default_encoding))

    def save_templates(self, data):
        self._template_file.write_text(
            json.dumps(data, indent=2),
            encoding=self._default_encoding,
        )

