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

  const addRow = () => {
    const emptyRow = {};
    cols.forEach((c) => {
      if (c.field) emptyRow[c.field] = "";
    });
    setRows((prev) => [...prev, emptyRow]);
  };

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
        <span className="pill">Grid editor</span>
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
          <button onClick={addRow}>➕ Add Row</button>
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
    </>
  );
}
