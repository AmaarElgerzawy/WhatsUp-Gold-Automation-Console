import { useEffect, useState } from "react";
import { apiCall } from "./utils/api";
import { API_BASE_URL } from "./utils/constants";

export default function DeviceUpTimeReport() {
  const [groups, setGroups] = useState([]);
  const [groupId, setGroupId] = useState("");
  const [groupName, setGroupName] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [loading, setLoading] = useState(false);
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiCall("reports/groups")
      .then((r) => r.json())
      .then(setGroups)
      .catch(() => setError("Failed to load groups"));
  }, []);

  const generate = async () => {
    if (!groupId || !start || !end) {
      alert("Select group and date range");
      return;
    }

    setLoading(true);
    setError("");
    setFile(null);

    try {
      const params = new URLSearchParams({
        group_id: groupId,
        group_name: groupName,
        start,
        end,
      });

      const res = await apiCall(`reports/uptime?${params.toString()}`, {
        method: "POST",
      });

      const data = await res.json();
      if (!res.ok) {
        setError(JSON.stringify(data));
      } else {
        setFile(data);
      }
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
          <h2 className="app-main-title">Device Uptime Report</h2>
          <p className="app-main-subtitle">
            Generate device uptime availability reports for any group and
            period.
          </p>
        </div>
        <span className="pill">On-Demand</span>
      </div>

      <section className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">Generate Uptime Report</h3>
            <p className="card-subtitle">
              Choose a device group and time range to generate your uptime Excel
              report.
            </p>
          </div>
        </div>

        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Device Group</label>
            <select
              className="select"
              value={groupId}
              onChange={(e) => {
                const g = groups.find((x) => x.id == e.target.value);
                if (g) {
                  setGroupId(g.id);
                  setGroupName(g.name);
                }
              }}
            >
              <option value="">Select group</option>
              {groups.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
              ))}
            </select>
          </div>
          <div className="from-group">
            <div className="form-group">
              <label className="form-label">Start Date</label>
              <div className="date-box">
                <input
                  className="input input--clean"
                  value={start}
                  type="date"
                  onChange={(e) => setStart(e.target.value)}
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">End Date</label>
              <div className="date-box">
                <input
                  className="input input--clean"
                  placeholder="YYYY-MM-DD"
                  value={end}
                  type="date"
                  onChange={(e) => setEnd(e.target.value)}
                />
              </div>
            </div>
          </div>
        </div>

        <div style={{ marginTop: 20, display: "flex", gap: 10 }}>
          <button
            type="button"
            className="button button--primary"
            onClick={generate}
            disabled={loading}
          >
            <span className="button-icon">📊</span>
            {loading ? "Generating…" : "Generate Report"}
          </button>
        </div>

        {error && <pre className="mono-output mono-output--error">{error}</pre>}

        {file && (
          <div style={{ marginTop: 20 }}>
            <div className="card" style={{ padding: 16 }}>
              <strong>Report ready:</strong>
              <div style={{ marginTop: 8 }}>
                <a
                  className="button button--primary"
                  href={`${API_BASE_URL}/reports/download?path=${encodeURIComponent(
                    file.path,
                  )}`}
                >
                  ⬇ Download {file.filename}
                </a>
              </div>
            </div>
          </div>
        )}
      </section>
    </>
  );
}
