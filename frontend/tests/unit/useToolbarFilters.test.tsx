import { act, cleanup, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useToolbarFilters } from '@/components/toolbar/useToolbarFilters';

const navigation = vi.hoisted(() => ({
  push: vi.fn(),
  query: '',
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: navigation.push }),
  useSearchParams: () => new URLSearchParams(navigation.query),
}));

function lastPushedParams(): URLSearchParams {
  const url = navigation.push.mock.calls.at(-1)?.[0];
  expect(url).toBeTypeOf('string');
  return new URL(url as string, 'https://internnexus.test').searchParams;
}

describe('useToolbarFilters', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    navigation.query = '';
    navigation.push.mockReset();
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it('preserves an existing search when a filter changes', () => {
    navigation.query = 'search=python';
    const { result } = renderHook(() => useToolbarFilters());

    act(() => {
      result.current.updateMultiSelect('company', ['Stripe']);
    });

    const params = lastPushedParams();
    expect(params.get('search')).toBe('python');
    expect(params.get('company')).toBe('Stripe');
  });

  it('preserves an existing filter when debounced search changes', () => {
    navigation.query = 'company=Stripe';
    const { result } = renderHook(() => useToolbarFilters());

    act(() => {
      result.current.setSearchInput('python');
    });

    act(() => {
      vi.advanceTimersByTime(400);
    });

    const params = lastPushedParams();
    expect(params.get('company')).toBe('Stripe');
    expect(params.get('search')).toBe('python');
  });

  it('composes rapid search then filter changes', () => {
    const { result } = renderHook(() => useToolbarFilters());

    act(() => {
      result.current.setSearchInput('python');
      result.current.updateMultiSelect('category', ['software_engineering']);
    });

    act(() => {
      vi.advanceTimersByTime(400);
    });

    const params = lastPushedParams();
    expect(params.get('search')).toBe('python');
    expect(params.get('category')).toBe('software_engineering');
  });

  it('composes rapid filter then search changes', () => {
    const { result } = renderHook(() => useToolbarFilters());

    act(() => {
      result.current.updateMultiSelect('company', ['Stripe']);
      result.current.setSearchInput('python');
    });

    act(() => {
      vi.advanceTimersByTime(400);
    });

    const params = lastPushedParams();
    expect(params.get('company')).toBe('Stripe');
    expect(params.get('search')).toBe('python');
  });

  it('clears search without removing filters', () => {
    navigation.query = 'search=python&company=Stripe';
    const { result } = renderHook(() => useToolbarFilters());

    act(() => {
      result.current.updateFilter('search', '');
    });

    const params = lastPushedParams();
    expect(params.has('search')).toBe(false);
    expect(params.get('company')).toBe('Stripe');
  });

  it('removes pagination when a filter changes', () => {
    navigation.query = 'page=3&search=python';
    const { result } = renderHook(() => useToolbarFilters());

    act(() => {
      result.current.updateMultiSelect('work_mode', ['remote']);
    });

    const params = lastPushedParams();
    expect(params.has('page')).toBe(false);
    expect(params.get('search')).toBe('python');
    expect(params.get('work_mode')).toBe('remote');
  });

  it('preserves matched mode when ordinary filters change', () => {
    navigation.query = 'matched=true&search=python';
    const { result } = renderHook(() => useToolbarFilters());

    act(() => {
      result.current.updateMultiSelect('work_mode', ['remote']);
    });

    const params = lastPushedParams();
    expect(params.get('matched')).toBe('true');
    expect(params.get('search')).toBe('python');
    expect(params.get('work_mode')).toBe('remote');
  });
});
