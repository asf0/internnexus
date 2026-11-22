export function formatDateTime(dateString: string): string {
  return new Date(dateString).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'UTC',
  });
}

export function formatDateShort(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  });
}

export function addUtmParams(baseUrl: string, source = 'internnexus'): string {
  try {
    const url = new URL(baseUrl);
    url.searchParams.set('utm_source', source);
    return url.toString();
  } catch {
    return baseUrl;
  }
}
