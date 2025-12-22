import { useEffect, useState } from "react";
import { apiCall } from "./utils/api";

export default function BackupRouters() {
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiCall("backup/routers")
      .then((res) => res.json())
      .then((data) => {
        setContent(data.content || "");
        setLoading(false);
      });
  }, []);

  const save = async () => {
    await apiCall("backup/routers", {
      method: "POST",
      body: JSON.stringify({ content }),
    });

    alert("Routers list saved");
  };

  if (loading) return <p>Loading...</p>;

  return (
    <>
      <div className="app-main-header">
        <div>
          <h2 className="app-main-title">Backup routers</h2>
          <p className="app-main-subtitle">
            Manage routers used for configuration backups
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
          placeholder={`One router IP per line\nExample:\n192.168.1.1\n192.168.1.2`}
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
          >
            💾 Save routers.txt
          </button>
        </div>
      </section>
    </>
  );
}
