import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useMatchState } from '@/lib/hooks/useMatchState';
import { LOCAL_STORAGE_KEYS, SESSION_STORAGE_KEYS } from '@/lib/constants';
import type { MatchResponse } from '@/lib/types/job';

// Mock localStorage/sessionStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
};
const sessionStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});
Object.defineProperty(window, 'sessionStorage', {
  value: sessionStorageMock,
});

describe('useMatchState', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.getItem.mockReturnValue(null);
    sessionStorageMock.getItem.mockReturnValue(null);
  });

  it('initializes with empty state when storage is empty', () => {
    // Act
    const { result } = renderHook(() => useMatchState());

    // Assert
    expect(result.current.sessionId).toBeNull();
    expect(result.current.matchScores.size).toBe(0);
    expect(result.current.isLoading).toBe(false);
  });

  it('loads match state from storage on mount', () => {
    // Arrange
    const storedSession = 'test-session-123';
    const storedScores = { 'job-1': 85, 'job-2': 70 };
    localStorageMock.getItem.mockImplementation((key: string) => {
      if (key === LOCAL_STORAGE_KEYS.MATCH_SCORES) return JSON.stringify(storedScores);
      return null;
    });
    sessionStorageMock.getItem.mockImplementation((key: string) => {
      if (key === SESSION_STORAGE_KEYS.MATCH_SESSION) return storedSession;
      return null;
    });

    // Act
    const { result } = renderHook(() => useMatchState());

    // Assert
    expect(result.current.sessionId).toBe(storedSession);
    expect(result.current.matchScores.get('job-1')).toBe(85);
    expect(result.current.matchScores.get('job-2')).toBe(70);
  });

  it('saves match scores to localStorage and session id to sessionStorage', () => {
    // Arrange
    const { result } = renderHook(() => useMatchState());
    const response: MatchResponse = {
      matches: [
        {
          job_id: 'job-1',
          score: 0.85,
          match_percentage: 85,
          title: 'Job 1',
          company: 'Co 1',
          location: 'NYC',
          apply_url: 'https://example.com/apply',
          description_text: 'Description',
        },
      ],
      total: 1,
      session_id: 'test-session-123',
      page: 1,
      page_size: 20,
      total_pages: 1,
    };

    // Act
    act(() => {
      result.current.saveMatches(response);
    });

    // Assert
    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      LOCAL_STORAGE_KEYS.MATCH_SCORES,
      JSON.stringify({ 'job-1': 85 })
    );
    expect(sessionStorageMock.setItem).toHaveBeenCalledWith(
      SESSION_STORAGE_KEYS.MATCH_SESSION,
      'test-session-123'
    );
  });

  it('clears matches from storage', () => {
    // Arrange
    const { result } = renderHook(() => useMatchState());

    // Act
    act(() => {
      result.current.clearMatches();
    });

    // Assert
    expect(localStorageMock.removeItem).toHaveBeenCalledWith(LOCAL_STORAGE_KEYS.MATCH_SCORES);
    expect(sessionStorageMock.removeItem).toHaveBeenCalledWith(SESSION_STORAGE_KEYS.MATCH_SESSION);
  });

  it('getMatchPercentage returns correct score', () => {
    // Arrange
    const { result } = renderHook(() => useMatchState());
    const response: MatchResponse = {
      matches: [
        {
          job_id: 'job-1',
          score: 0.85,
          match_percentage: 85,
          title: 'Job 1',
          company: 'Co 1',
          location: 'NYC',
          apply_url: 'https://example.com/apply',
          description_text: 'Description',
        },
      ],
      total: 1,
      session_id: 'test-session-123',
      page: 1,
      page_size: 20,
      total_pages: 1,
    };

    act(() => {
      result.current.saveMatches(response);
    });

    // Act & Assert
    expect(result.current.getMatchPercentage('job-1')).toBe(85);
    expect(result.current.getMatchPercentage('non-existent')).toBeUndefined();
  });
});
