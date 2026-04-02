import { useEffect, useState } from "react";
import { apiCall } from "./utils/api";

const defaultSchedule = {
  enabled: false,
  mode: "interval",
  interval_seconds: 3600,
  run_time: "02:00",
  run_on_startup: false,
};

export default function ConfigBackups() {
  const [devices, setDevices] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState("");
  const [files, setFiles] = useState([]);
  const [content, setContent] = useState("");
  const [running, setRunning] = useState(false);
  const [schedule, setSchedule] = useState(defaultSchedule);
  const [scheduleLoading, setScheduleLoading] = useState(true);
  const [scheduleSaving, setScheduleSaving] = useState(false);

  useEffect(() => {
    apiCall("backups/devices")
      .then((res) => res.json())
      .then(setDevices);
  }, []);

  useEffect(() => {
    let cancelled = false;
    setScheduleLoading(true);
    apiCall("backups/schedule")
      .then((res) => res.json())
      .then((data) => {
        if (!cancelled && data && typeof data === "object") {
          setSchedule({ ...defaultSchedule, ...data });
        }
      })
      .catch(() => {
        if (!cancelled) setSchedule(defaultSchedule);
      })
      .finally(() => {
        if (!cancelled) setScheduleLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const refreshDevices = async () => {
    const res = await apiCall("backups/devices");
    setDevices(await res.json());
  };

  const runBackups = async () => {
    setRunning(true);
    try {
      await apiCall("backups/run", { method: "POST" });
      setSelectedDevice("");
      setFiles([]);
      setContent("");
      await refreshDevices();
    } finally {
      setRunning(false);
    }
  };

  const saveSchedule = async () => {
    setScheduleSaving(true);
    try {
      const body = {
        enabled: Boolean(schedule.enabled),
        mode: schedule.mode === "daily" ? "daily" : "interval",
        interval_seconds: Math.max(
          60,
          Math.min(604800, Number(schedule.interval_seconds) || 3600)
        ),
        run_time: (schedule.run_time || "02:00").slice(0, 5),
        run_on_startup: Boolean(schedule.run_on_startup),
      };
      const res = await apiCall("backups/schedule", {
        method: "PUT",
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.text();
        alert(err || "Failed to save schedule");
        return;
      }
      const data = await res.json();
      if (data.schedule) setSchedule({ ...defaultSchedule, ...data.schedule });
    } finally {
      setScheduleSaving(false);
    }
  };

  const intervalMinutes = Math.max(
    1,
    Math.round((Number(schedule.interval_seconds) || 3600) / 60)
  );

  const setIntervalFromMinutes = (minutes) => {
    const m = Math.max(1, Math.min(10080, Number(minutes) || 60));
    setSchedule((s) => ({ ...s, interval_seconds: m * 60 }));
  };

  const loadFiles = async (device) => {
    setSelectedDevice(device);
    setContent("");
    const res = await apiCall(`backups/${device}`);
    setFiles(await res.json());
  };

  const viewFile = async (file) => {
    const res = await apiCall(`backups/${selectedDevice}/${file}`);
    const text = await res.text();
    setContent(text.replace(/\\n/g, "\n"));
  };

  return (
    <>
      <div className="app-main-header">
        <div>
          <h2 className="app-main-title">Config backups</h2>
          <p className="app-main-subtitle">
            Explore snapshots, run backups on demand, and choose when scheduled
            backups run (server local time for daily runs).
          </p>
        </div>
        <span className="pill">Backups</span>
      </div>

      <section className="card" style={{ marginBottom: 16 }}>
        <h4 className="card-title" style={{ marginBottom: 8 }}>
          Schedule
        </h4>
        {scheduleLoading ? (
          <p className="card-subtitle">Loading schedule…</p>
        ) : (
          <>
            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                marginBottom: 12,
              }}
            >
              <input
                type="checkbox"
                checked={Boolean(schedule.enabled)}
                onChange={(e) =>
                  setSchedule((s) => ({ ...s, enabled: e.target.checked }))
                }
              />
              <span>Enable scheduled backups</span>
            </label>

            <div style={{ marginBottom: 12 }}>
              <span className="card-subtitle" style={{ marginRight: 8 }}>
                Run
              </span>
              <select
                value={schedule.mode === "daily" ? "daily" : "interval"}
                onChange={(e) =>
                  setSchedule((s) => ({
                    ...s,
                    mode: e.target.value === "daily" ? "daily" : "interval",
                  }))
                }
                style={{ padding: "6px 8px", borderRadius: 6 }}
              >
                <option value="interval">every</option>
                <option value="daily">once per day at</option>
              </select>
              {schedule.mode === "daily" ? (
                <input
                  type="time"
                  value={(schedule.run_time || "02:00").slice(0, 5)}
                  onChange={(e) =>
                    setSchedule((s) => ({ ...s, run_time: e.target.value }))
                  }
                  style={{ marginLeft: 8, padding: "6px 8px", borderRadius: 6 }}
                />
              ) : (
                <>
                  <input
                    type="number"
                    min={1}
                    max={10080}
                    value={intervalMinutes}
                    onChange={(e) => setIntervalFromMinutes(e.target.value)}
                    style={{
                      width: 80,
                      marginLeft: 8,
                      padding: "6px 8px",
                      borderRadius: 6,
                    }}
                  />
                  <span style={{ marginLeft: 6 }}>minutes</span>
                </>
              )}
            </div>

            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                marginBottom: 12,
              }}
            >
              <input
                type="checkbox"
                checked={Boolean(schedule.run_on_startup)}
                onChange={(e) =>
                  setSchedule((s) => ({
                    ...s,
                    run_on_startup: e.target.checked,
                  }))
                }
              />
              <span>Also run once when the API server starts (if schedule is enabled)</span>
            </label>

            <button
              type="button"
              className="button button--secondary"
              onClick={saveSchedule}
              disabled={scheduleSaving}
            >
              {scheduleSaving ? "Saving…" : "Save schedule"}
            </button>
          </>
        )}
      </section>

      <section className="card">
        <div className="two-column-layout" style={{ alignItems: "flex-start" }}>
          <div style={{ gridColumn: "1 / -1", marginBottom: 8 }}>
            <button
              type="button"
              className="button button--primary"
              onClick={runBackups}
              disabled={running}
              style={{ width: "100%" }}
            >
              {running ? "Taking backups..." : "Take backups now"}
            </button>
          </div>

          {/* Devices */}
          <div>
            <h4 className="card-title" style={{ marginBottom: 8 }}>
              Devices
            </h4>
            <ul className="list">
              {devices.map((d) => (
                <li key={d} style={{ marginBottom: 4 }}>
                  <button
                    type="button"
                    className="list-item-button"
                    onClick={() => loadFiles(d)}
                  >
                    <span>{d}</span>
                    {selectedDevice === d && (
                      <span className="tag">Selected</span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          </div>

          {/* Files + content */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "220px minmax(0, 1fr)",
              gap: 12,
            }}
          >
            <div>
              <h4 className="card-title" style={{ marginBottom: 8 }}>
                Configs
              </h4>
              <ul className="list">
                {files.map((f) => (
                  <li key={f} style={{ marginBottom: 4 }}>
                    <button
                      type="button"
                      className="list-item-button"
                      onClick={() => viewFile(f)}
                    >
                      <span>{f}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h4 className="card-title" style={{ marginBottom: 8 }}>
                Content
              </h4>
              {content ? (
                <pre className="mono-output">{content}</pre>
              ) : (
                <p className="card-subtitle">
                  Select a device and a backup file to view its content.
                </p>
              )}
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
