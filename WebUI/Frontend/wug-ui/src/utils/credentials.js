import { apiCall } from "./api";

/**
 * Saved credential metadata the current user may use (no passwords).
 * @returns {Promise<Array<{id, name, username, description}>>}
 */
export async function fetchEligibleCredentials() {
  const res = await apiCall("credentials/eligible");
  if (!res.ok) return [];
  return res.json();
}

/**
 * Full vault (secrets included) — admin only.
 */
export async function fetchAdminCredentials() {
  const res = await apiCall("admin/credentials");
  if (!res.ok) return [];
  return res.json();
}

export async function createAdminCredential({
  name,
  username,
  password,
  enablePassword = "",
  description = "",
}) {
  const fd = new FormData();
  fd.append("name", name.trim());
  fd.append("username", username.trim());
  fd.append("password", password);
  fd.append("enable_password", enablePassword || "");
  fd.append("description", description.trim());
  return apiCall("admin/credentials", { method: "POST", body: fd });
}

export async function updateAdminCredential(
  id,
  { name, username, password, enablePassword, description },
) {
  const fd = new FormData();
  fd.append("name", name.trim());
  fd.append("username", username.trim());
  if (password !== undefined && password !== null && String(password).trim()) {
    fd.append("password", password);
  }
  if (enablePassword !== undefined && enablePassword !== null && String(enablePassword).trim()) {
    fd.append("enable_password", enablePassword);
  }
  fd.append("description", (description || "").trim());
  return apiCall(`admin/credentials/${encodeURIComponent(id)}`, {
    method: "PUT",
    body: fd,
  });
}

export async function deleteAdminCredential(id) {
  return apiCall(`admin/credentials/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}
