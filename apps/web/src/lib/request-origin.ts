export function requestOrigin(headers: Headers, fallbackOrigin: string): string {
  const proto = headers.get("x-forwarded-proto")?.split(",")[0]?.trim();
  const host = headers.get("x-forwarded-host")?.split(",")[0]?.trim();
  if (proto && host) return `${proto}://${host}`;
  return fallbackOrigin;
}
