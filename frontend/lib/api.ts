import type { User } from "@/lib/types";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api").replace(/\/$/, "");
const ACCESS_KEY = "triageiq_access";
const REFRESH_KEY = "triageiq_refresh";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACCESS_KEY);
}

export function clearTokens(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ACCESS_KEY);
  window.localStorage.removeItem(REFRESH_KEY);
}

function saveTokens(access: string, refresh: string): void {
  window.localStorage.setItem(ACCESS_KEY, access);
  window.localStorage.setItem(REFRESH_KEY, refresh);
}

async function refreshAccessToken(): Promise<string | null> {
  const refresh = typeof window === "undefined" ? null : window.localStorage.getItem(REFRESH_KEY);
  if (!refresh) return null;
  const response = await fetch(`${API_BASE}/auth/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });
  if (!response.ok) {
    clearTokens();
    return null;
  }
  const data = (await response.json()) as { access: string; refresh?: string };
  window.localStorage.setItem(ACCESS_KEY, data.access);
  if (data.refresh) window.localStorage.setItem(REFRESH_KEY, data.refresh);
  return data.access;
}

export class ApiError extends Error {
  constructor(message: string, public status: number, public fields?: unknown) {
    super(message);
  }
}

export async function apiFetch<T>(path: string, options: RequestInit = {}, retry = true): Promise<T> {
  const access = getAccessToken();
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (access) headers.set("Authorization", `Bearer ${access}`);

  const response = await fetch(`${API_BASE}${path.startsWith("/") ? path : `/${path}`}`, {
    ...options,
    headers,
    cache: "no-store",
  });

  if (response.status === 401 && retry) {
    const nextToken = await refreshAccessToken();
    if (nextToken) return apiFetch<T>(path, options, false);
  }

  if (!response.ok) {
    let message = `Request failed with status ${response.status}.`;
    let fields: unknown;
    try {
      const body = await response.json();
      message = body?.error?.message || body?.detail || message;
      fields = body?.error?.fields;
    } catch {
      // Keep the generic message.
    }
    throw new ApiError(message, response.status, fields);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export async function login(email: string, password: string): Promise<User> {
  const response = await fetch(`${API_BASE}/auth/token/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) throw new ApiError("Email or password is incorrect.", response.status);
  const tokens = (await response.json()) as { access: string; refresh: string };
  saveTokens(tokens.access, tokens.refresh);
  return apiFetch<User>("/auth/me/");
}

export async function downloadIncidentReport(incidentId: string, draft: boolean): Promise<void> {
  const access = getAccessToken();
  const response = await fetch(`${API_BASE}/incidents/${incidentId}/report/${draft ? "?draft=true" : ""}`, {
    headers: access ? { Authorization: `Bearer ${access}` } : {},
  });
  if (!response.ok) throw new ApiError("The report could not be generated.", response.status);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = response.headers.get("content-disposition")?.match(/filename="?([^\"]+)/)?.[1] || "triageiq-report.pdf";
  link.click();
  URL.revokeObjectURL(url);
}
