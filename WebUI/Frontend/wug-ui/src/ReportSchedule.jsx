import { useEffect, useState } from "react";
import { AgGridReact } from "ag-grid-react";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";
import { apiCall } from "./utils/api";

export default function ReportSchedule() {
  const [rows, setRows] = useState([]);
  const [cols, setCols] = useState([]);
  const [gridApi, setGridApi] = useState(null);
  const [newCol, setNewCol] = useState("");
  const [showDialog, setShowDialog] = useState(false);
  const [dialogMode, setDialogMode] = useState("simple"); // simple | weeklyWindow
  const [dialogGroup, setDialogGroup] = useState("");
  const [dialogReportType, setDialogReportType] = useState("both"); // availability | uptime | both
  const [dialogEvery, setDialogEvery] = useState(1);
  const [dialogUnit, setDialogUnit] = useState("d"); // m, h, d, w
  const [runDay, setRunDay] = useState("mon");
  const [runTime, setRunTime] = useState("10:00");
  const [windowFromDateTime, setWindowFromDateTime] = useState("");
  const [windowToDateTime, setWindowToDateTime] = useState("");

  useEffect(() => {
    apiCall("reports/schedule")
      .then((res) => {
        if (!res.ok) {
          throw new Error(`Failed to load schedule: ${res.statusText}`);
        }
        return res.json();
      })
      .then((data) => {
        // Known core scheduling fields in preferred order
        const coreFields = [
          "group",
          "availability_period",
          "availability_window_start",
          "availability_window_end",
          "uptime_period",
          "uptime_window_start",
          "uptime_window_end",
        ];

        // Columns returned from backend (JSON schedule or legacy)
        const backendColumns = Array.isArray(data.columns) ? data.columns : [];

        // Merge: ensure all core fields exist first, then any extra columns
        const mergedFields = Array.from(
          new Set([...coreFields, ...backendColumns])
        );

        const columnFromField = (field) => {
          if (!field) return null;

          // Nicely formatted header titles for known fields
          const niceHeader = (() => {
            switch (field) {
              case "group":
                return "Group name";
              case "availability_period":
                return "Availability period (e.g. 1d, 1w)";
              case "availability_window_start":
                return "Availability window start offset";
              case "availability_window_end":
                return "Availability window end offset";
              case "uptime_period":
                return "Uptime period (e.g. 1d, 1w)";
              case "uptime_window_start":
                return "Uptime window start offset";
              case "uptime_window_end":
                return "Uptime window end offset";
              default:
                return field;
            }
          })();

          return {
            headerName: niceHeader,
            field,
            editable: true,
            minWidth: 160,
            cellClass: "excel-cell",
          };
        };

        const columnDefs = [
          {
            headerName: "",
            valueGetter: "node.rowIndex + 1",
            width: 48,
            pinned: "left",
            cellClass: "excel-row-number",
            headerClass: "excel-row-number-header",
            suppressMenu: true,
          },
          ...mergedFields
            .map((field) => columnFromField(field))
            .filter(Boolean),
        ];

        setRows(data.rows);
        setCols(columnDefs);

        setTimeout(() => {
          if (gridApi) gridApi.sizeColumnsToFit();
        }, 0);
      });
  }, [gridApi]);

  // ---------- ROW / COLUMN ACTIONS ----------

  const deleteRow = () => {
    if (!gridApi) return;
    const selected = gridApi.getSelectedNodes();
    if (!selected.length) return;

    const toDelete = selected[0].data;
    setRows((prev) => prev.filter((r) => r !== toDelete));
  };

  const addColumn = () => {
    if (!newCol.trim()) return;

    const colDef = {
      headerName: newCol,
      field: newCol,
      editable: true,
      minWidth: 120,
      cellClass: "excel-cell",
    };

    setCols((prev) => [...prev, colDef]);

    setRows((prev) =>
      prev.map((r) => ({
        ...r,
        [newCol]: "",
      }))
    );

    setNewCol("");
  };

  // ---------- SAVE ----------

  const save = async () => {
    const updated = [];
    gridApi.forEachNode((n) => updated.push(n.data));

    // Persist both rows and the active column fields so the backend
    // can round‑trip additional / custom columns.
    const columnFields = cols
      .filter((c) => c.field)
      .map((c) => c.field);

    await apiCall("reports/schedule", {
      method: "POST",
      body: JSON.stringify({
        columns: columnFields,
        rows: updated,
      }),
    });

    alert("Saved successfully");
  };

  return (
    <>
      <div className="app-main-header">
        <div>
          <h2 className="app-main-title">Report schedule</h2>
          <p className="app-main-subtitle">
            Manage when and how reports are generated and delivered. This
            schedule is now stored server-side as JSON (no Excel dependency).
          </p>
        </div>
        <span className="pill">Scheduler</span>
      </div>

      <section className="card">
        {/* ===== Toolbar ===== */}
        <div
          style={{
            display: "flex",
            gap: 8,
            marginBottom: 12,
            alignItems: "center",
          }}
        >
          <button
            type="button"
            className="button"
            onClick={() => {
              setDialogGroup("");
              setDialogReportType("both");
              setDialogEvery(1);
              setDialogUnit("d");
              setDialogMode("simple");
              setRunDay("mon");
              setRunTime("10:00");
              setWindowFromDateTime("");
              setWindowToDateTime("");
              setShowDialog(true);
            }}
          >
            ➕ New schedule
          </button>
          <button onClick={deleteRow}>➖ Delete Row</button>

          <input
            placeholder="New column name"
            value={newCol}
            onChange={(e) => setNewCol(e.target.value)}
            style={{ marginLeft: 16 }}
          />
          <button onClick={addColumn}>➕ Add Column</button>
        </div>

        {/* ===== Grid ===== */}
        <div
          className="ag-theme-alpine excel-grid"
          style={{
            width: "100%",
            borderRadius: 8,
            border: "1px solid #e5e7eb",
          }}
        >
          <AgGridReact
            rowData={rows}
            columnDefs={cols}
            domLayout="autoHeight"
            rowSelection="single"
            defaultColDef={{
              resizable: true,
              editable: true,
            }}
            rowHeight={36}
            headerHeight={36}
            stopEditingWhenCellsLoseFocus={true}
            onGridReady={(p) => {
              setGridApi(p.api);
              p.api.sizeColumnsToFit();
            }}
          />
        </div>

        {/* ===== Footer ===== */}
        <div
          style={{
            marginTop: 16,
            display: "flex",
            justifyContent: "flex-end",
            borderTop: "1px solid #e5e7eb",
            paddingTop: 12,
          }}
        >
          <button
            type="button"
            className="button button--primary"
            onClick={save}
          >
            💾 Save schedule
          </button>
        </div>
      </section>

      {/* Simple dialog to add a new schedule entry */}
      {showDialog && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(15,23,42,0.4)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 50,
          }}
        >
          <div
            className="card"
            style={{
              width: 420,
              maxWidth: "90vw",
              padding: 20,
              boxShadow: "0 10px 25px rgba(15,23,42,0.4)",
            }}
          >
            <h3 className="card-title" style={{ marginBottom: 8 }}>
              New report schedule
            </h3>
            <p className="card-subtitle" style={{ marginBottom: 16 }}>
              Choose group, report type, and either a simple interval or an
              exact weekly window (e.g. Monday 10:00 to Friday 10:00).
            </p>

            {/* Mode toggle */}
            <div
              style={{
                display: "flex",
                gap: 8,
                marginBottom: 12,
              }}
            >
              <button
                type="button"
                className={
                  "button" +
                  (dialogMode === "simple" ? " button--primary" : "")
                }
                onClick={() => setDialogMode("simple")}
              >
                Simple interval
              </button>
              <button
                type="button"
                className={
                  "button" +
                  (dialogMode === "weeklyWindow" ? " button--primary" : "")
                }
                onClick={() => setDialogMode("weeklyWindow")}
              >
                Weekly window
              </button>
            </div>

            <div className="form-group">
              <label className="form-label">Group name</label>
              <input
                className="input"
                placeholder="Exact group name in WhatsUp"
                value={dialogGroup}
                onChange={(e) => setDialogGroup(e.target.value)}
              />
            </div>

            <div className="form-group" style={{ marginTop: 12 }}>
              <label className="form-label">Report type</label>
              <select
                className="select"
                value={dialogReportType}
                onChange={(e) => setDialogReportType(e.target.value)}
              >
                <option value="availability">Availability only</option>
                <option value="uptime">Device Uptime only</option>
                <option value="both">Both (Availability + Uptime)</option>
              </select>
            </div>

            {dialogMode === "simple" && (
              <div
                className="form-group"
                style={{ marginTop: 12, display: "flex", gap: 8 }}
              >
                <div style={{ flex: 1 }}>
                  <label className="form-label">Every</label>
                  <input
                    className="input"
                    type="number"
                    min={1}
                    value={dialogEvery}
                    onChange={(e) =>
                      setDialogEvery(
                        Number.isNaN(parseInt(e.target.value, 10))
                          ? 1
                          : Math.max(1, parseInt(e.target.value, 10))
                      )
                    }
                  />
                </div>
                <div style={{ flex: 1 }}>
                  <label className="form-label">Unit</label>
                  <select
                    className="select"
                    value={dialogUnit}
                    onChange={(e) => setDialogUnit(e.target.value)}
                  >
                    <option value="h">Hours</option>
                    <option value="d">Days</option>
                    <option value="w">Weeks</option>
                  </select>
                </div>
              </div>
            )}

            {dialogMode === "weeklyWindow" && (
              <div style={{ marginTop: 12 }}>
                <div
                  className="form-group"
                  style={{ display: "flex", gap: 8, marginBottom: 8 }}
                >
                  <div style={{ flex: 1 }}>
                    <label className="form-label">Run on (day)</label>
                    <select
                      className="select"
                      value={runDay}
                      onChange={(e) => setRunDay(e.target.value)}
                    >
                      <option value="mon">Monday</option>
                      <option value="tue">Tuesday</option>
                      <option value="wed">Wednesday</option>
                      <option value="thu">Thursday</option>
                      <option value="fri">Friday</option>
                      <option value="sat">Saturday</option>
                      <option value="sun">Sunday</option>
                    </select>
                  </div>
                  <div style={{ flex: 1 }}>
                    <label className="form-label">Run at (time)</label>
                    <input
                      className="input"
                      type="time"
                      value={runTime}
                      onChange={(e) => setRunTime(e.target.value)}
                    />
                  </div>
                </div>

                <div className="form-group" style={{ marginBottom: 8 }}>
                  <label className="form-label">Window start (date &amp; time)</label>
                  <input
                    className="input"
                    type="datetime-local"
                    value={windowFromDateTime}
                    onChange={(e) => setWindowFromDateTime(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Window end (date &amp; time)</label>
                  <input
                    className="input"
                    type="datetime-local"
                    value={windowToDateTime}
                    onChange={(e) => setWindowToDateTime(e.target.value)}
                  />
                </div>
              </div>
            )}

            <div
              style={{
                marginTop: 20,
                display: "flex",
                justifyContent: "flex-end",
                gap: 8,
              }}
            >
              <button
                type="button"
                className="button"
                onClick={() => setShowDialog(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="button button--primary"
                onClick={() => {
                  if (!dialogGroup.trim()) {
                    alert("Please enter a group name.");
                    return;
                  }

                  const base = { group: dialogGroup.trim() };

                  if (dialogMode === "simple") {
                    const period = `${dialogEvery}${dialogUnit}`;

                    if (
                      dialogReportType === "availability" ||
                      dialogReportType === "both"
                    ) {
                      base.availability_period = period;
                    }
                    if (
                      dialogReportType === "uptime" ||
                      dialogReportType === "both"
                    ) {
                      base.uptime_period = period;
                    }
                  } else if (dialogMode === "weeklyWindow") {
                    if (!windowFromDateTime || !windowToDateTime) {
                      alert("Please enter both window start and end date & time.");
                      return;
                    }

                    // Helper to map day -> index (Mon=0)
                    const dayIndex = (d) => {
                      const map = {
                        mon: 0,
                        tue: 1,
                        wed: 2,
                        thu: 3,
                        fri: 4,
                        sat: 5,
                        sun: 6,
                      };
                      return map[d] ?? 0;
                    };

                    const toMinutesFromDayAndTime = (day, time) => {
                      const [h, m] = time.split(":").map((v) => parseInt(v, 10));
                      const hour = Number.isNaN(h) ? 0 : h;
                      const minute = Number.isNaN(m) ? 0 : m;
                      return dayIndex(day) * 24 * 60 + hour * 60 + minute;
                    };

                    const toMinutesFromDateTime = (value) => {
                      if (!value || typeof value !== "string") return null;
                      const [datePart, timePart] = value.split("T");
                      if (!datePart || !timePart) return null;

                      const [year, month, day] = datePart
                        .split("-")
                        .map((v) => parseInt(v, 10));
                      const jsDate = new Date(
                        Number.isNaN(year) ? 1970 : year,
                        Number.isNaN(month) ? 0 : month - 1,
                        Number.isNaN(day) ? 1 : day
                      );

                      const weekday = jsDate.getDay(); // 0=Sun..6=Sat
                      const weekdayToKey = {
                        1: "mon",
                        2: "tue",
                        3: "wed",
                        4: "thu",
                        5: "fri",
                        6: "sat",
                        0: "sun",
                      };
                      const dayKey = weekdayToKey[weekday] || "mon";

                      const [h, m] = timePart
                        .split(":")
                        .map((v) => parseInt(v, 10));
                      const hour = Number.isNaN(h) ? 0 : h;
                      const minute = Number.isNaN(m) ? 0 : m;

                      const timeStr = `${String(hour).padStart(2, "0")}:${String(
                        minute
                      ).padStart(2, "0")}`;

                      return toMinutesFromDayAndTime(dayKey, timeStr);
                    };

                    const runMinutes = toMinutesFromDayAndTime(runDay, runTime);
                    const fromMinutes = toMinutesFromDateTime(windowFromDateTime);
                    const toMinutesVal = toMinutesFromDateTime(windowToDateTime);

                    if (
                      fromMinutes === null ||
                      toMinutesVal === null ||
                      Number.isNaN(fromMinutes) ||
                      Number.isNaN(toMinutesVal)
                    ) {
                      alert(
                        "Invalid window start or end. Please use a valid date & time."
                      );
                      return;
                    }

                    const diffToToken = (minutesDiff) => {
                      if (minutesDiff % 60 === 0) {
                        const hours = minutesDiff / 60;
                        return `${hours}h`;
                      }
                      return `${minutesDiff}m`;
                    };

                    const startDiff = fromMinutes - runMinutes;
                    const endDiff = toMinutesVal - runMinutes;

                    // Weekly cadence
                    const period = "1w";

                    if (
                      dialogReportType === "availability" ||
                      dialogReportType === "both"
                    ) {
                      base.availability_period = period;
                      base.availability_window_start = diffToToken(startDiff);
                      base.availability_window_end = diffToToken(endDiff);
                    }
                    if (
                      dialogReportType === "uptime" ||
                      dialogReportType === "both"
                    ) {
                      base.uptime_period = period;
                      base.uptime_window_start = diffToToken(startDiff);
                      base.uptime_window_end = diffToToken(endDiff);
                    }
                  }

                  setRows((prev) => [...prev, base]);
                  setShowDialog(false);
                }}
              >
                Add schedule
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
