import { act, cleanup, renderHook, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useJobDetail } from '@/components/jobs/useJobDetail';

const jobDetail = {
  id: '00000000-0000-0000-0000-000000000001',
  source: 'greenhouse',
  title: 'Software Intern',
  company: 'Acme',
  location: 'Remote',
  city: null,
  state: null,
  country: null,
  apply_url: 'https://example.com/apply',
  description_html: '<p>Build useful software.</p>',
  job_category: 'software_engineering',
  job_type: 'internship',
  work_mode: 'remote',
  posted_at: null,
  is_active: true,
};

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('useJobDetail', () => {
  it('loads a full job only after an id is selected', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(jobDetail), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    );
    vi.stubGlobal('fetch', fetchMock);

    const { result, rerender } = renderHook(({ jobId }) => useJobDetail(jobId), {
      initialProps: { jobId: null as string | null },
    });

    expect(fetchMock).not.toHaveBeenCalled();

    rerender({ jobId: jobDetail.id });
    await waitFor(() =>
      expect(result.current.detail?.description_html).toBe(jobDetail.description_html)
    );

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(`/api/jobs/${jobDetail.id}`, expect.anything());
  });

  it('aborts an obsolete request when selection changes', async () => {
    let resolveFirst: (response: Response) => void = () => {};
    const firstResponse = new Promise<Response>((resolve) => {
      resolveFirst = resolve;
    });
    const secondJob = {
      ...jobDetail,
      id: '00000000-0000-0000-0000-000000000002',
      title: 'Data Intern',
      description_html: '<p>Build data systems.</p>',
    };
    const fetchMock = vi
      .fn()
      .mockReturnValueOnce(firstResponse)
      .mockResolvedValueOnce(
        new Response(JSON.stringify(secondJob), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      );
    vi.stubGlobal('fetch', fetchMock);

    const { result, rerender } = renderHook(({ jobId }) => useJobDetail(jobId), {
      initialProps: { jobId: jobDetail.id as string | null },
    });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    const firstSignal = (fetchMock.mock.calls[0][1] as RequestInit).signal;
    rerender({ jobId: secondJob.id });

    expect(result.current.detail).toBeNull();
    expect(result.current.isLoading).toBe(true);

    await waitFor(() =>
      expect(result.current.detail?.description_html).toBe(secondJob.description_html)
    );
    expect(firstSignal?.aborted).toBe(true);

    resolveFirst(
      new Response(JSON.stringify(jobDetail), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    );
    await act(async () => Promise.resolve());

    expect(result.current.detail?.description_html).toBe(secondJob.description_html);
  });

  it('exposes an error and can retry', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 503 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify(jobDetail), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      );
    vi.stubGlobal('fetch', fetchMock);

    const { result } = renderHook(() => useJobDetail(jobDetail.id));
    await waitFor(() => expect(result.current.error).toBeTruthy());

    act(() => result.current.retry());

    await waitFor(() =>
      expect(result.current.detail?.description_html).toBe(jobDetail.description_html)
    );
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('marks a missing job as unavailable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 404 })));

    const { result } = renderHook(() => useJobDetail(jobDetail.id));

    await waitFor(() => expect(result.current.isUnavailable).toBe(true));
    expect(result.current.error).toBe('This job is no longer available.');
  });
});
