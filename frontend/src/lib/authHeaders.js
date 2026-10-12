/** Token → request headers. Empty token attaches nothing. */

export function getBearerlessToken(value) {
  return String(value ?? "")
    .replace(/^Bearer\s+/i, "")
    .trim();
}

export function buildAuthHeaders(token) {
  const trimmed = String(token ?? "").trim();
  if (!trimmed) {
    return {};
  }
  const apiKey = getBearerlessToken(trimmed);
  if (!apiKey) {
    return {};
  }
  return {
    Authorization: /^Bearer\s+/i.test(trimmed) ? trimmed : `Bearer ${apiKey}`,
    "X-API-Key": apiKey,
  };
}
