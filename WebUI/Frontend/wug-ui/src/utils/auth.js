import { apiUrl } from "./config";
import {
  STORAGE_KEYS,
  ENDPOINTS,
  AUTH_HEADER_KEY,
  AUTH_HEADER_PREFIX,
} from "./constants";

export function getToken() {
  return localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
}

export function setToken(token) {
  localStorage.setItem(STORAGE_KEYS.AUTH_TOKEN, token);
}

export function removeToken() {
  localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN);
}

export function getUser() {
  const userStr = localStorage.getItem(STORAGE_KEYS.USER);
  return userStr ? JSON.parse(userStr) : null;
}

export function setUser(user) {
  localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user));
}

export function removeUser() {
  localStorage.removeItem(STORAGE_KEYS.USER);
}

export function logout() {
  removeToken();
  removeUser();
}

export function getAuthHeaders() {
  const token = getToken();
  return token
    ? {
        [AUTH_HEADER_KEY]: `${AUTH_HEADER_PREFIX} ${token}`,
      }
    : {};
}

export async function checkAuth() {
  const token = getToken();
  if (!token) {
    return null;
  }

  try {
    const res = await fetch(apiUrl(ENDPOINTS.AUTH_ME), {
      headers: getAuthHeaders(),
    });

    if (!res.ok) {
      logout();
      return null;
    }

    const user = await res.json();
    setUser(user);
    return user;
  } catch (e) {
    logout();
    return null;
  }
}

export async function checkPageAccess(page) {
  const token = getToken();
  if (!token) {
    return false;
  }

  try {
    const res = await fetch(
      apiUrl(`${ENDPOINTS.AUTH_CHECK_PAGE_ACCESS}?page=${page}`),
      {
        headers: getAuthHeaders(),
      }
    );

    if (!res.ok) {
      return false;
    }

    const data = await res.json();
    return data.has_access;
  } catch (e) {
    return false;
  }
}
