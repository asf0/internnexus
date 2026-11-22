import { act, cleanup, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useJobActions } from '@/components/jobs/useJobActions';

const actions = vi.hoisted(() => ({
  saveJob: vi.fn(),
  unsaveJob: vi.fn(),
  markApplied: vi.fn(),
  unmarkApplied: vi.fn(),
  trackJobClick: vi.fn(),
}));

vi.mock('@/app/actions/user', () => ({
  saveJob: actions.saveJob,
  unsaveJob: actions.unsaveJob,
  markApplied: actions.markApplied,
  unmarkApplied: actions.unmarkApplied,
}));

vi.mock('@/app/actions/jobs', () => ({
  trackJobClick: actions.trackJobClick,
}));

describe('useJobActions', () => {
  beforeEach(() => {
    Object.values(actions).forEach((mock) => mock.mockReset());
  });

  afterEach(() => {
    cleanup();
  });

  it('shows pending and success feedback while saving a job', async () => {
    let resolveSave: (value: { success: boolean }) => void = () => {};
    actions.saveJob.mockReturnValue(
      new Promise((resolve) => {
        resolveSave = resolve;
      })
    );
    const { result } = renderHook(() =>
      useJobActions({
        isAuthenticated: true,
        initialSavedJobIds: [],
        initialAppliedJobIds: [],
      })
    );

    let savePromise!: Promise<void>;
    act(() => {
      savePromise = result.current.handleToggleSave('job-1', true);
    });
    expect(result.current.pendingSaveJobIds.has('job-1')).toBe(true);

    await act(async () => {
      resolveSave({ success: true });
      await savePromise;
    });

    expect(result.current.savedJobIds.has('job-1')).toBe(true);
    expect(result.current.pendingSaveJobIds.has('job-1')).toBe(false);
    expect(result.current.actionToast).toEqual({ type: 'success', message: 'Job saved.' });
  });

  it('surfaces backend failures when marking an application', async () => {
    actions.markApplied.mockResolvedValue({ success: false, error: 'Service unavailable' });
    const { result } = renderHook(() =>
      useJobActions({
        isAuthenticated: true,
        initialSavedJobIds: [],
        initialAppliedJobIds: [],
      })
    );

    await act(async () => {
      await result.current.handleToggleApplied('job-1', true);
    });

    expect(result.current.appliedJobIds.has('job-1')).toBe(false);
    expect(result.current.actionToast).toEqual({
      type: 'error',
      message: 'Service unavailable',
    });
  });

  it('explains that application tracking requires sign-in', async () => {
    const { result } = renderHook(() =>
      useJobActions({
        isAuthenticated: false,
        initialSavedJobIds: [],
        initialAppliedJobIds: [],
      })
    );

    await act(async () => {
      await result.current.handleToggleApplied('job-1', true);
    });

    await waitFor(() => {
      expect(result.current.actionToast).toEqual({
        type: 'info',
        message: 'Sign in to track your applications.',
      });
    });
    expect(actions.markApplied).not.toHaveBeenCalled();
  });
});
