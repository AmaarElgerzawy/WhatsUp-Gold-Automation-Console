const STORAGE_KEY = "wug_credentials";

export function getAllCredentials() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch (e) {
    return [];
  }
}

export function saveCredential(cred) {
  const all = getAllCredentials();
  const existingIndex = all.findIndex((c) => c.id === cred.id);

  if (existingIndex >= 0) {
    all[existingIndex] = cred;
  } else {
    all.push(cred);
  }

  localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
  // Dispatch custom event for same-window updates
  window.dispatchEvent(new Event("credentialsUpdated"));
  return cred;
}

export function deleteCredential(id) {
  const all = getAllCredentials();
  const filtered = all.filter((c) => c.id !== id);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
  // Dispatch custom event for same-window updates
  window.dispatchEvent(new Event("credentialsUpdated"));
}

export function getCredential(id) {
  const all = getAllCredentials();
  return all.find((c) => c.id === id);
}

export function createCredentialId() {
  return `cred_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}
