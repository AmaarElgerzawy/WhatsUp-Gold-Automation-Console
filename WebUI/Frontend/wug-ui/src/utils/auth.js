import { apiUrl } from "./config";

const TOKEN_KEY = "wug_auth_token";
const USER_KEY = "wug_user";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function removeToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export function getUser() {
  const userStr = localStorage.getItem(USER_KEY);
  return userStr ? JSON.parse(userStr) : null;
}

export function setUser(user) {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function removeUser() {
  localStorage.removeItem(USER_KEY);
}

export function logout() {
  removeToken();
  removeUser();
}

export function getAuthHeaders() {
  const token = getToken();
  return token
    ? {
        Authorization: `Bearer ${token}`,
      }
    : {};
}

export async function checkAuth() {
  const token = getToken();
  if (!token) {
    return null;
  }

  try {
    const res = await fetch(apiUrl("auth/me"), {
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
    const res = await fetch(apiUrl(`auth/check-page-access?page=${page}`), {
      headers: getAuthHeaders(),
    });

    if (!res.ok) {
      return false;
    }

    const data = await res.json();
    return data.has_access;
  } catch (e) {
    return false;
  }
}
