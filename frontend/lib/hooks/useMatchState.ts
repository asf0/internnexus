import { useState, useCallback, useEffect } from 'react';
import { LOCAL_STORAGE_KEYS, SESSION_STORAGE_KEYS } from '@/lib/constants';
import type { MatchResponse } from '@/lib/types/job';

const MATCH_STATE_UPDATED_EVENT = 'internnexus:match-state-updated';

interface MatchState {
  sessionId: string | null;
  matchScores: Map<string, number>;
  isLoading: boolean;
}

export function useMatchState() {
  const [state, setState] = useState<MatchState>({
    sessionId: null,
    matchScores: new Map(),
    isLoading: true,
  });

  const loadFromStorage = useCallback(() => {
    const storedSessionId = sessionStorage.getItem(SESSION_STORAGE_KEYS.MATCH_SESSION);
    const storedScores = localStorage.getItem(LOCAL_STORAGE_KEYS.MATCH_SCORES);
    let scores: Record<string, number> = {};

    if (storedScores) {
      try {
        const parsed = JSON.parse(storedScores) as Record<string, number>;
        scores = parsed && typeof parsed === 'object' ? parsed : {};
      } catch {
        scores = {};
      }
    }

    setState({
      sessionId: storedSessionId || null,
      matchScores: new Map(Object.entries(scores)),
      isLoading: false,
    });
  }, []);

  useEffect(() => {
    loadFromStorage();

    const onStorage = (event: StorageEvent) => {
      if (event.key === LOCAL_STORAGE_KEYS.MATCH_SCORES) {
        loadFromStorage();
      }
    };
    const onLocalUpdate = () => loadFromStorage();

    window.addEventListener('storage', onStorage);
    window.addEventListener(MATCH_STATE_UPDATED_EVENT, onLocalUpdate);
    return () => {
      window.removeEventListener('storage', onStorage);
      window.removeEventListener(MATCH_STATE_UPDATED_EVENT, onLocalUpdate);
    };
  }, [loadFromStorage]);

  const saveMatches = useCallback((response: MatchResponse) => {
    const scoresMap: Record<string, number> = {};
    response.matches.forEach((match) => {
      scoresMap[match.job_id] = match.match_percentage;
    });

    sessionStorage.setItem(SESSION_STORAGE_KEYS.MATCH_SESSION, response.session_id);
    localStorage.setItem(LOCAL_STORAGE_KEYS.MATCH_SCORES, JSON.stringify(scoresMap));
    window.dispatchEvent(new Event(MATCH_STATE_UPDATED_EVENT));

    setState({
      sessionId: response.session_id,
      matchScores: new Map(Object.entries(scoresMap)),
      isLoading: false,
    });

    return response.session_id;
  }, []);

  const clearMatches = useCallback(() => {
    localStorage.removeItem(LOCAL_STORAGE_KEYS.MATCH_SCORES);
    sessionStorage.removeItem(SESSION_STORAGE_KEYS.MATCH_SESSION);
    window.dispatchEvent(new Event(MATCH_STATE_UPDATED_EVENT));
    setState({
      sessionId: null,
      matchScores: new Map(),
      isLoading: false,
    });
  }, []);

  const getMatchPercentage = useCallback(
    (jobId: string): number | undefined => {
      return state.matchScores.get(jobId);
    },
    [state.matchScores]
  );

  return {
    ...state,
    saveMatches,
    clearMatches,
    getMatchPercentage,
  };
}
