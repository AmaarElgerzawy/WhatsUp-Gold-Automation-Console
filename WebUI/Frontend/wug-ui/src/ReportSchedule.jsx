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
          ...data.columns.map((c) => ({
            headerName: c,
            field: c,
            editable: true,
            minWidth: 120,
            cellClass: "excel-cell",
          })),
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

    await apiCall("reports/schedule", {
      method: "POST",
      body: JSON.stringify({ rows: updated }),
    });

    alert("Saved successfully");
  };

  return (
    <>
      <div className="app-main-header">
        <div>
          <h2 className="app-main-title">Report schedule</h2>
          <p className="app-main-subtitle">
            Manage when and how reports are generated and delivered.
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
