from __future__ import annotations

import pyodbc

from constants import get_connection_string


class DbConnectionFactory:
    def get_conn(self):
        return pyodbc.connect(get_connection_string())

