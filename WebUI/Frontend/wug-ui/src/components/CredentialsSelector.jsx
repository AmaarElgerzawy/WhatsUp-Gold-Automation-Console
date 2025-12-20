import { useState, useEffect } from "react";
import { getAllCredentials, getCredential } from "../utils/credentials";

export default function CredentialsSelector({
  selectedId,
  onSelect,
  onCredentialsChange,
  showManualEntry = true,
}) {
  const [credentials, setCredentials] = useState([]);
  const [showManual, setShowManual] = useState(!selectedId);

  const loadCredentials = () => {
    const creds = getAllCredentials();
    setCredentials(creds);
    if (creds.length === 0 && !showManualEntry) {
      setShowManual(true);
    }
  };

  useEffect(() => {
    loadCredentials();
  }, []);

  // Refresh when localStorage changes (e.g., credentials added/removed)
  useEffect(() => {
    const handleStorageChange = () => {
      loadCredentials();
      if (onCredentialsChange) {
        onCredentialsChange();
      }
    };
    window.addEventListener("storage", handleStorageChange);
    // Also listen to custom event for same-window updates
    window.addEventListener("credentialsUpdated", handleStorageChange);
    return () => {
      window.removeEventListener("storage", handleStorageChange);
      window.removeEventListener("credentialsUpdated", handleStorageChange);
    };
  }, [onCredentialsChange]);

  const handleSelect = (id) => {
    if (id === "manual") {
      setShowManual(true);
      onSelect(null);
      return;
    }

    const cred = getCredential(id);
    if (cred) {
      setShowManual(false);
      onSelect(cred);
    } else {
      // Credential not found, fall back to manual
      setShowManual(true);
      onSelect(null);
    }
  };

  return (
    <div className="form-group">
      <label className="form-label">Credentials</label>
      {credentials.length > 0 && (
        <select
          className="select"
          value={selectedId || "manual"}
          onChange={(e) => handleSelect(e.target.value)}
          style={{ marginBottom: showManual ? 12 : 0 }}
        >
          <option value="manual">Enter manually</option>
          {credentials.map((cred) => (
            <option key={cred.id} value={cred.id}>
              {cred.name} ({cred.username})
            </option>
          ))}
        </select>
      )}

      {showManual && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <span className="helper-text" style={{ fontSize: 11 }}>
            {credentials.length > 0
              ? "Or enter credentials manually below"
              : "No saved credentials. Enter manually or create one in the Credentials page."}
          </span>
        </div>
      )}
    </div>
  );
}
