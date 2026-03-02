import { useEffect, useState } from "react";
import { apiCall } from "./utils/api";
import { API_BASE_URL } from "./utils/constants";

export default function ManualReports() {
  const [groups, setGroups] = useState([]);
  const [groupId, setGroupId] = useState("");
  const [groupName, setGroupName] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [periodPreset, setPeriodPreset] = useState("custom");
  const [loading, setLoading] = useState(false);
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiCall("reports/groups")
      .then((r) => r.json())
      .then(setGroups)
      .catch(() => setError("Failed to load groups"));
  }, []);

  const toLocalInput = (date) => {
    if (!(date instanceof Date)) return "";
    const pad = (n) => String(n).padStart(2, "0");
    const year = date.getFullYear();
    const month = pad(date.getMonth() + 1);
    const day = pad(date.getDate());
    const hours = pad(date.getHours());
    const minutes = pad(date.getMinutes());
    return `${year}-${month}-${day}T${hours}:${minutes}`;
  };

  const applyPreset = (preset) => {
    const now = new Date();

    if (preset === "last_week_work_window") {
      // Last week: Monday 10:00 → Friday 10:00
      const day = now.getDay(); // 0=Sun..6=Sat
      const mondayThisWeek = new Date(now);
      const diffToMonday = (day + 6) % 7; // how many days since Monday
      mondayThisWeek.setDate(now.getDate() - diffToMonday);
      mondayThisWeek.setHours(10, 0, 0, 0);

      const mondayLastWeek = new Date(mondayThisWeek);
      mondayLastWeek.setDate(mondayThisWeek.getDate() - 7);

      const fridayLastWeek = new Date(mondayLastWeek);
      fridayLastWeek.setDate(mondayLastWeek.getDate() + 4);
      fridayLastWeek.setHours(10, 0, 0, 0);

      setStart(toLocalInput(mondayLastWeek));
      setEnd(toLocalInput(fridayLastWeek));
      return;
    }

    if (preset === "full_last_month") {
      // Full previous calendar month
      const firstThisMonth = new Date(now.getFullYear(), now.getMonth(), 1, 0, 0, 0, 0);
      let firstPrevMonth;
      if (firstThisMonth.getMonth() === 0) {
        firstPrevMonth = new Date(firstThisMonth.getFullYear() - 1, 11, 1, 0, 0, 0, 0);
      } else {
        firstPrevMonth = new Date(firstThisMonth.getFullYear(), firstThisMonth.getMonth() - 1, 1, 0, 0, 0, 0);
      }

      setStart(toLocalInput(firstPrevMonth));
      setEnd(toLocalInput(firstThisMonth));
      return;
    }
  };

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

      const res = await apiCall(`reports/manual?${params.toString()}`, {
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
          <h2 className="app-main-title">Manual Reports</h2>
          <p className="app-main-subtitle">
            Generate availability reports for any group and any period.
          </p>
        </div>
        <span className="pill">On-Demand</span>
      </div>

      <section className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">Generate Report</h3>
            <p className="card-subtitle">
              Choose a group and time range, then generate your Excel report.
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
              <label className="form-label">Report period</label>
              <select
                className="select"
                value={periodPreset}
                onChange={(e) => {
                  const value = e.target.value;
                  setPeriodPreset(value);
                  if (value !== "custom") {
                    applyPreset(value);
                  }
                }}
              >
                <option value="custom">Custom (choose dates)</option>
                <option value="last_week_work_window">
                  Last week: Monday 10:00 → Friday 10:00
                </option>
                <option value="full_last_month">Full last month</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Start Date & Time</label>
              <div className="date-box">
                <input
                  className="input input--clean"
                  value={start}
                  type="datetime-local"
                  onChange={(e) => setStart(e.target.value)}
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">End Date & Time</label>
              <div className="date-box">
                <input
                  className="input input--clean"
                  placeholder="YYYY-MM-DDTHH:mm"
                  value={end}
                  type="datetime-local"
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
                    file.path
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
