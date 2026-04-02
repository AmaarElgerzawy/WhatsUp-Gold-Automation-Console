from __future__ import annotations

from constants import QUERY_DEVICE_GROUPS, QUERY_DEVICE_TYPES


class DeviceLookupRepository:
    def __init__(self, db_factory) -> None:
        self._db_factory = db_factory

    def load_device_types(self):
        conn = self._db_factory.get_conn()
        cur = conn.cursor()
        cur.execute(QUERY_DEVICE_TYPES)
        data = {r.sDisplayName.strip(): r.nDeviceTypeID for r in cur.fetchall()}
        conn.close()
        return data

    def load_device_groups(self):
        conn = self._db_factory.get_conn()
        cur = conn.cursor()
        cur.execute(QUERY_DEVICE_GROUPS)
        data = {r.sGroupName.strip(): r.nDeviceGroupID for r in cur.fetchall()}
        conn.close()
        return data

