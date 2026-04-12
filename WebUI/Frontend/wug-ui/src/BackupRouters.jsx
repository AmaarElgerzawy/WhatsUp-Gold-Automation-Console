import { useEffect, useState } from "react";
import { apiCall } from "./utils/api";

export default function BackupRouters({ onSaved } = {}) {
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    apiCall("backup/routers")
      .then((res) => res.json())
      .then((data) => {
        setContent(data.content || "");
        setLoading(false);
      });
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      const res = await apiCall("backup/routers", {
        method: "POST",
        body: JSON.stringify({ content }),
      });
      if (!res.ok) {
        let msg = `Save failed (${res.status})`;
        try {
          const err = await res.json();
          if (err?.detail)
            msg =
              typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
        } catch {
          /* ignore */
        }
        alert(msg);
        return;
      }
      const data = await res.json().catch(() => ({}));
      try {
        await onSaved?.();
      } catch (e) {
        alert(
          e?.message
            ? `Saved routers.txt, but reloading credentials failed: ${e.message}`
            : "Saved routers.txt, but reloading credentials failed. Try refreshing the page.",
        );
        return;
      }
      const reloadEditor = await apiCall("backup/routers");
      if (reloadEditor.ok) {
        const refreshed = await reloadEditor.json().catch(() => ({}));
        setContent(refreshed.content ?? "");
      }
      if (
        typeof data.line_count === "number" &&
        data.line_count === 0 &&
        content.trim()
      ) {
        alert(
          "The server reported 0 host lines saved while the editor was not empty (only # comments or blank lines?).",
        );
        return;
      }
      alert(
        typeof data.credentials_merged === "number" && data.credentials_merged > 0
          ? `Saved: ${data.line_count} host(s) in the editor; ${data.credentials_merged} line(s) had credentials stored. The list below is updated.`
          : "Routers list saved. The credential list below has been refreshed.",
      );
    } catch (e) {
      alert(e?.message ? `Save failed: ${e.message}` : "Save failed (network error).");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <p>Loading...</p>;

  return (
    <>
      <div className="app-main-header">
        <div>
          <h2 className="app-main-title">Backup routers</h2>
          <p className="app-main-subtitle">
            Paste or type <strong>host,username,password,enable</strong> (one router per
            line) from your other files, then <strong>Save routers.txt</strong>. Passwords
            are moved into secure storage and the editor is replaced with{" "}
            <strong>one IP or hostname per line</strong> only. Edit username / passwords
            below when you need to change them.
          </p>
        </div>
        <span className="pill">Text editor</span>
      </div>

      <section
        className="card"
        style={{ overflow: "hidden", padding: "10px", boxSizing: "border-box" }}
      >
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          spellCheck={false}
          style={{
            minHeight: "300px",
            fontFamily: "monospace",
            fontSize: 14,
            padding: 12,
            borderRadius: 6,
            border: "1px solid #d1d5db",
            width: "-webkit-fill-available",
          }}
          placeholder={`Paste from your file — one line per router:\n192.168.1.1,myuser,mypass,myenable\n192.168.1.2,admin,secret,\n\nAfter Save, only IPs stay here; passwords move to the table below.\n\nYou can also save host-only lines and set passwords only in the table.\nEnable password: leave empty after the last comma if not used.`}
        />

        <div
          style={{
            marginTop: 16,
            display: "flex",
            justifyContent: "flex-end",
          }}
        >
          <button
            type="button"
            className="button button--primary"
            onClick={save}
            disabled={saving}
          >
            {saving ? "Saving…" : "💾 Save routers.txt"}
          </button>
        </div>
      </section>
    </>
  );
}
