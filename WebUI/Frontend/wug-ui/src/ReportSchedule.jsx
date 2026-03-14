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
  const [dialogMode, setDialogMode] = useState("weekly");
  const [dialogGroup, setDialogGroup] = useState("");
  const [runDay, setRunDay] = useState("sun");
  const [runTime, setRunTime] = useState("10:00");
  const [windowFromDay, setWindowFromDay] = useState("fri");
  const [windowFromTime, setWindowFromTime] = useState("00:00");
  const [windowToDay, setWindowToDay] = useState("sun");
  const [windowToTime, setWindowToTime] = useState("02:00");
  // Monthly trigger
  const [runDayOfMonth, setRunDayOfMonth] = useState(1);
  const [periodStartDay, setPeriodStartDay] = useState(1);
  const [periodEndDay, setPeriodEndDay] = useState(5);
  const [periodStartTime, setPeriodStartTime] = useState("00:00");
  const [periodEndTime, setPeriodEndTime] = useState("23:59");

  useEffect(() => {
    apiCall("reports/schedule")
      .then((res) => {
        if (!res.ok) {
          throw new Error(`Failed to load schedule: ${res.statusText}`);
        }
        return res.json();
      })
      .then((data) => {
        // type: "weekly" | "monthly", group, then mode-specific fields
        const coreFields = [
          "group",
          "type",
          "run_day",
          "run_time",
          "period_start_day",
          "period_start_time",
          "period_end_day",
          "period_end_time",
          "run_day_of_month",
        ];

        // Columns returned from backend (JSON schedule or legacy)
        const backendColumns = Array.isArray(data.columns) ? data.columns : [];

        // Merge: ensure all core fields exist first, then any extra columns
        const mergedFields = Array.from(
          new Set([...coreFields, ...backendColumns])
        ).filter((f) => f !== "id");

        const columnFromField = (field) => {
          if (!field) return null;

          // Nicely formatted header titles for known fields
          const niceHeader = (() => {
            switch (field) {
              case "group":
                return "Group name";
              case "type":
                return "Schedule type (weekly | monthly)";
              case "run_day":
                return "Run day (weekday, weekly)";
              case "run_time":
                return "Run time (HH:MM)";
              case "period_start_day":
                return "Period start day (weekday or day of month)";
              case "period_start_time":
                return "Period start time";
              case "period_end_day":
                return "Period end day (weekday or day of month)";
              case "period_end_time":
                return "Period end time";
              case "run_day_of_month":
                return "Run day of month (1–31, monthly)";
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

  const persistSchedule = async (rowsToSave) => {
    // Persist both rows and the active column fields so the backend
    // can round‑trip additional / custom columns.
    const columnFields = cols
      .filter((c) => c.field)
      .map((c) => c.field)
      .filter((f) => f !== "id");

    await apiCall("reports/schedule", {
      method: "POST",
      body: JSON.stringify({
        columns: columnFields,
        rows: rowsToSave,
      }),
    });
  };

  const deleteRow = () => {
    if (!gridApi) return;
    const selected = gridApi.getSelectedNodes();
    if (!selected.length) return;

    const toDelete = selected[0].data;
    const nextRows = rows.filter((r) => r !== toDelete);
    setRows(nextRows);

    // Auto-save deletions so removed schedules stop executing immediately.
    persistSchedule(nextRows)
      .then(() => alert("Deleted and saved successfully"))
      .catch((e) => alert(`Failed to save deletion: ${e}`));
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
    await persistSchedule(updated);

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
              setDialogMode("weekly");
              setRunDay("sun");
              setRunTime("10:00");
              setWindowFromDay("fri");
              setWindowFromTime("00:00");
              setWindowToDay("sun");
              setWindowToTime("02:00");
              setRunDayOfMonth(1);
              setPeriodStartDay(1);
              setPeriodEndDay(5);
              setPeriodStartTime("00:00");
              setPeriodEndTime("23:59");
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
              Trigger &amp; window: run on a specific day and time; data window is
              relative to run (weekly) or previous month (monthly).
            </p>

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
                  (dialogMode === "weekly" ? " button--primary" : "")
                }
                onClick={() => setDialogMode("weekly")}
              >
                Weekly
              </button>
              <button
                type="button"
                className={
                  "button" +
                  (dialogMode === "monthly" ? " button--primary" : "")
                }
                onClick={() => setDialogMode("monthly")}
              >
                Monthly
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

            {dialogMode === "weekly" && (
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

                <div
                  className="form-group"
                  style={{ display: "flex", gap: 8, marginBottom: 8 }}
                >
                  <div style={{ flex: 1 }}>
                    <label className="form-label">Window start (day)</label>
                    <select
                      className="select"
                      value={windowFromDay}
                      onChange={(e) => setWindowFromDay(e.target.value)}
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
                    <label className="form-label">Window start (time)</label>
                    <input
                      className="input"
                      type="time"
                      value={windowFromTime}
                      onChange={(e) => setWindowFromTime(e.target.value)}
                    />
                  </div>
                </div>

                <div
                  className="form-group"
                  style={{ display: "flex", gap: 8 }}
                >
                  <div style={{ flex: 1 }}>
                    <label className="form-label">Window end (day)</label>
                    <select
                      className="select"
                      value={windowToDay}
                      onChange={(e) => setWindowToDay(e.target.value)}
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
                    <label className="form-label">Window end (time)</label>
                    <input
                      className="input"
                      type="time"
                      value={windowToTime}
                      onChange={(e) => setWindowToTime(e.target.value)}
                    />
                  </div>
                </div>
              </div>
            )}

            {dialogMode === "monthly" && (
              <div style={{ marginTop: 12 }}>
                <div
                  className="form-group"
                  style={{ display: "flex", gap: 8, marginBottom: 8 }}
                >
                  <div style={{ flex: 1 }}>
                    <label className="form-label">Run on day of month (1–31)</label>
                    <input
                      className="input"
                      type="number"
                      min={1}
                      max={31}
                      value={runDayOfMonth}
                      onChange={(e) =>
                        setRunDayOfMonth(
                          Math.min(31, Math.max(1, parseInt(e.target.value, 10) || 1))
                        )
                      }
                    />
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
                <div
                  className="form-group"
                  style={{ display: "flex", gap: 8, marginBottom: 8 }}
                >
                  <div style={{ flex: 1 }}>
                    <label className="form-label">Data window: start day (prev month, 1–31)</label>
                    <input
                      className="input"
                      type="number"
                      min={1}
                      max={31}
                      value={periodStartDay}
                      onChange={(e) =>
                        setPeriodStartDay(
                          Math.min(31, Math.max(1, parseInt(e.target.value, 10) || 1))
                        )
                      }
                    />
                  </div>
                  <div style={{ flex: 1 }}>
                    <label className="form-label">Data window: end day (prev month, 1–31)</label>
                    <input
                      className="input"
                      type="number"
                      min={1}
                      max={31}
                      value={periodEndDay}
                      onChange={(e) =>
                        setPeriodEndDay(
                          Math.min(31, Math.max(1, parseInt(e.target.value, 10) || 1))
                        )
                      }
                    />
                  </div>
                </div>
                <div
                  className="form-group"
                  style={{ display: "flex", gap: 8 }}
                >
                  <div style={{ flex: 1 }}>
                    <label className="form-label">Window start time</label>
                    <input
                      className="input"
                      type="time"
                      value={periodStartTime}
                      onChange={(e) => setPeriodStartTime(e.target.value)}
                    />
                  </div>
                  <div style={{ flex: 1 }}>
                    <label className="form-label">Window end time</label>
                    <input
                      className="input"
                      type="time"
                      value={periodEndTime}
                      onChange={(e) => setPeriodEndTime(e.target.value)}
                    />
                  </div>
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

                  if (dialogMode === "weekly") {
                    base.type = "weekly";
                    base.run_day = runDay;
                    base.run_time = runTime;
                    base.period_start_day = windowFromDay;
                    base.period_start_time = windowFromTime;
                    base.period_end_day = windowToDay;
                    base.period_end_time = windowToTime;
                  } else if (dialogMode === "monthly") {
                    if (periodEndDay < periodStartDay) {
                      alert("Period end day must be >= start day.");
                      return;
                    }
                    base.type = "monthly";
                    base.run_day_of_month = runDayOfMonth;
                    base.run_time = runTime;
                    base.period_start_day = periodStartDay;
                    base.period_start_time = periodStartTime;
                    base.period_end_day = periodEndDay;
                    base.period_end_time = periodEndTime;
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
