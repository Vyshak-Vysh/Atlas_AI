// Token storage. localStorage is fine here — this app has no SSR pages
// that need the token server-side (every authenticated page fetches
// client-side), and the alternative (an httpOnly cookie) would require a
// server proxy this build doesn't have.

const ACCESS_TOKEN_KEY = "atlasai.access_token";
const REFRESH_TOKEN_KEY = "atlasai.refresh_token";
const TENANT_ID_KEY = "atlasai.tenant_id";
const USER_ID_KEY = "atlasai.user_id";

export interface StoredSession {
  accessToken: string;
  refreshToken: string;
  tenantId: string;
  userId: string;
}

export function saveSession(session: StoredSession): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, session.accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, session.refreshToken);
  localStorage.setItem(TENANT_ID_KEY, session.tenantId);
  localStorage.setItem(USER_ID_KEY, session.userId);
}

export function loadSession(): StoredSession | null {
  if (typeof window === "undefined") return null;
  const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
  const tenantId = localStorage.getItem(TENANT_ID_KEY);
  const userId = localStorage.getItem(USER_ID_KEY);
  if (!accessToken || !refreshToken || !tenantId || !userId) return null;
  return { accessToken, refreshToken, tenantId, userId };
}

export function updateAccessToken(accessToken: string, refreshToken: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearSession(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(TENANT_ID_KEY);
  localStorage.removeItem(USER_ID_KEY);
}
