import { useState, useEffect, useCallback } from "react";
import { fetchEligibleCredentials } from "../utils/credentials";

export default function CredentialsSelector({
  selectedId,
  onSelect,
  onCredentialsChange,
  showManualEntry = true,
}) {
  const [credentials, setCredentials] = useState([]);
  const [showManual, setShowManual] = useState(!selectedId);

  const loadCredentials = useCallback(async () => {
    const creds = await fetchEligibleCredentials();
    setCredentials(Array.isArray(creds) ? creds : []);
    if ((!creds || creds.length === 0) && !showManualEntry) {
      setShowManual(true);
    }
  }, [showManualEntry]);

  useEffect(() => {
    loadCredentials();
  }, [loadCredentials]);

  useEffect(() => {
    const handleStorageChange = () => {
      loadCredentials();
      if (onCredentialsChange) {
        onCredentialsChange();
      }
    };
    window.addEventListener("storage", handleStorageChange);
    window.addEventListener("credentialsUpdated", handleStorageChange);
    return () => {
      window.removeEventListener("storage", handleStorageChange);
      window.removeEventListener("credentialsUpdated", handleStorageChange);
    };
  }, [loadCredentials, onCredentialsChange]);

  const handleSelect = (id) => {
    if (id === "manual") {
      setShowManual(true);
      onSelect(null);
      return;
    }

    const cred = credentials.find((c) => c.id === id);
    if (cred) {
      setShowManual(false);
      onSelect(cred);
    } else {
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
              : "No saved credentials assigned to you. Enter manually, or ask an administrator to assign credential sets."}
          </span>
        </div>
      )}
    </div>
  );
}
