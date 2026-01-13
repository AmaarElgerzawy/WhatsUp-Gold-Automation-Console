import { useState } from "react";
import { apiCall } from "./utils/api";
import {
  ENDPOINTS,
  OPERATIONS,
  FORM_FIELDS,
  UI_LABELS,
  ICONS,
  ERROR_MESSAGES,
  SPACING,
} from "./utils/constants";

function BulkChnages() {
  const [operation, setOperation] = useState(OPERATIONS.ADD);
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [output, setOutput] = useState("");
  const [error, setError] = useState("");
  const [configName, setConfigName] = useState("");
  const [logName, setLogName] = useState("");

  const downloadTemplate = async () => {
    try {
      const res = await apiCall(`${ENDPOINTS.BULK_TEMPLATE}/${operation}`, {
        method: "GET",
      });

      if (!res.ok) {
        alert(ERROR_MESSAGES.TEMPLATE_DOWNLOAD_FAILED);
        return;
      }

      const blob = await res.blob();

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");

      a.href = url;
      a.download = `bulk_${operation}_template.xlsx`;
      document.body.appendChild(a);
      a.click();

      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      alert(ERROR_MESSAGES.TEMPLATE_DOWNLOAD_ERROR);
    }
  };

  const run = async () => {
    if (!file) {
      alert(ERROR_MESSAGES.NO_FILE_SELECTED);
      return;
    }

    setLoading(true);
    setOutput("");
    setError("");

    const formData = new FormData();
    formData.append(FORM_FIELDS.OPERATION, operation);
    formData.append(FORM_FIELDS.FILE, file);
    formData.append(FORM_FIELDS.CONFIG_NAME, configName.trim());
    formData.append(FORM_FIELDS.LOG_NAME, logName.trim());

    try {
      const res = await apiCall(ENDPOINTS.RUN_BULK, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (!res.ok) {
        setError(JSON.stringify(data, null, 2));
        setLoading(false);
        return;
      }

      setOutput(
        `EXIT CODE: ${data.returncode}\n\n` +
          `STDOUT:\n${data.stdout}\n\n` +
          `STDERR:\n${data.stderr}`
      );
    } catch (e) {
      setError(e.toString());
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="app-main-header">
        <div>
          <h2 className="app-main-title">{UI_LABELS.BULK}</h2>
          <p className="app-main-subtitle">
            Import an Excel sheet and safely apply large‑scale changes.
          </p>
        </div>
        <span className="pill">{UI_LABELS.EXCEL_DRIVEN}</span>
      </div>

      <section className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">{UI_LABELS.UPLOAD_AND_RUN}</h3>
            <p className="card-subtitle">
              Select the action and the Excel file that contains your devices.
            </p>
          </div>
          <div className="card-actions">
            <button
              className="button button--ghost button--sm"
              type="button"
              onClick={downloadTemplate}
            >
              <span className="button-icon">{ICONS.DOCUMENT}</span>
              {UI_LABELS.DOWNLOAD_TEMPLATE}
            </button>
          </div>
        </div>

        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">{UI_LABELS.OPERATION}</label>
            <select
              className="select"
              value={operation}
              onChange={(e) => setOperation(e.target.value)}
            >
              <option value={OPERATIONS.ADD}>Add devices</option>
              <option value={OPERATIONS.DELETE}>Delete devices</option>
              <option value={OPERATIONS.UPDATE}>Update devices</option>
            </select>
            <span className="helper-text">
              Choose what you want to do with the devices listed in the Excel
              file.
            </span>
          </div>

          <div className="form-group">
            <label className="form-label">{UI_LABELS.FILE}</label>
            <input
              className="input"
              type="file"
              accept=".xlsx"
              onChange={(e) => setFile(e.target.files[0])}
            />
            <span className="helper-text">
              The first row should contain column headers.
            </span>
          </div>
        </div>

        <div className="form-grid" style={{ marginTop: SPACING.MD }}>
          <div className="form-group">
            <label className="form-label">{UI_LABELS.CONFIG_NAME}</label>
            <input
              className="input"
              placeholder="Leave blank for auto-generated name"
              value={configName}
              onChange={(e) => setConfigName(e.target.value)}
            />
            <span className="helper-text">
              Custom name for saved config file. If empty, uses timestamp.
            </span>
          </div>

          <div className="form-group">
            <label className="form-label">{UI_LABELS.LOG_NAME}</label>
            <input
              className="input"
              placeholder="Leave blank for auto-generated name"
              value={logName}
              onChange={(e) => setLogName(e.target.value)}
            />
            <span className="helper-text">
              Custom name for saved log file. If empty, uses timestamp.
            </span>
          </div>
        </div>

        <div
          style={{ marginTop: SPACING.LG, display: "flex", gap: SPACING.SM }}
        >
          <button
            className="button button--primary"
            onClick={run}
            disabled={loading}
            type="button"
          >
            <span className="button-icon">▶</span>
            {loading ? "Running…" : "Run bulk operation"}
          </button>
        </div>

        {error && <pre className="mono-output mono-output--error">{error}</pre>}

        {output && !error && <pre className="mono-output">{output}</pre>}
      </section>
    </>
  );
}

export default BulkChnages;
