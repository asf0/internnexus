export function createAuthHeaders(
  token: string,
  extra: Record<string, string> = {}
): Record<string, string> {
  return {
    ...extra,
    Authorization: `Bearer ${token}`,
  };
}

export function createOptionalAuthHeaders(
  token: string | undefined
): Record<string, string> | undefined {
  return token ? createAuthHeaders(token) : undefined;
}
