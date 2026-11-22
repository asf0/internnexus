export type JobDetailView = { description_html: string; description_truncated?: boolean };

function isJobDetailView(value: unknown): value is JobDetailView {
  return (
    typeof value === 'object' &&
    value !== null &&
    !Array.isArray(value) &&
    typeof (value as Record<string, unknown>).description_html === 'string'
  );
}

export async function fetchJobDetail(
  id: string,
  signal?: AbortSignal
): Promise<JobDetailView | null> {
  const response = await fetch(`/api/jobs/${id}`, { cache: 'no-store', signal });
  if (response.status >= 400 && response.status < 500) return null;
  if (!response.ok) throw new Error(`Unable to load job details (${response.status})`);
  const payload: unknown = await response.json();
  if (!isJobDetailView(payload)) throw new Error('Invalid job detail response');
  return payload;
}
