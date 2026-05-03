const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "/api/v1";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("autods_token");
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const isFormData = options.body instanceof FormData;

  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (!isFormData) headers["Content-Type"] = "application/json";

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (res.status === 401) {
    if (typeof window !== "undefined") {
      localStorage.removeItem("autods_token");
      window.location.href = "/login";
    }
    throw new Error("Unauthorized");
  }

  if (res.status === 429) {
    throw new Error("Rate limit exceeded");
  }

  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      message = (body as { detail?: string; message?: string }).detail ??
        (body as { message?: string }).message ??
        message;
    } catch {
      // ignore parse failure
    }
    throw new Error(message);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  get<T>(path: string): Promise<T> {
    return apiFetch<T>(path);
  },
  post<T>(path: string, body?: unknown): Promise<T> {
    return apiFetch<T>(path, {
      method: "POST",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  },
  patch<T>(path: string, body?: unknown): Promise<T> {
    return apiFetch<T>(path, {
      method: "PATCH",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  },
  del<T>(path: string): Promise<T> {
    return apiFetch<T>(path, { method: "DELETE" });
  },
  upload<T>(path: string, formData: FormData): Promise<T> {
    return apiFetch<T>(path, { method: "POST", body: formData });
  },
};
