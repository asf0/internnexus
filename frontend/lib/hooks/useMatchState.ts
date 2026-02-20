import { useState, useCallback, useEffect } from "react";
import { LOCAL_STORAGE_KEYS } from "@/lib/constants";
import type { MatchResponse } from "@/lib/types/job";

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

  useEffect(() => {
    const storedSessionId = localStorage.getItem(LOCAL_STORAGE_KEYS.MATCH_SESSION);
    const storedScores = localStorage.getItem(LOCAL_STORAGE_KEYS.MATCH_SCORES);

    const sessionId = storedSessionId || null;
    const scores: Record<string, number> = storedScores ? JSON.parse(storedScores) : {};

    setState({
      sessionId,
      matchScores: new Map(Object.entries(scores)),
      isLoading: false,
    });
  }, []);

  const saveMatches = useCallback((response: MatchResponse) => {
    const scoresMap: Record<string, number> = {};
    response.matches.forEach((match) => {
      scoresMap[match.job_id] = match.match_percentage;
    });

    localStorage.setItem(LOCAL_STORAGE_KEYS.MATCH_SESSION, response.session_id);
    localStorage.setItem(LOCAL_STORAGE_KEYS.MATCH_SCORES, JSON.stringify(scoresMap));

    setState({
      sessionId: response.session_id,
      matchScores: new Map(Object.entries(scoresMap)),
      isLoading: false,
    });

    return response.session_id;
  }, []);

  const clearMatches = useCallback(() => {
    localStorage.removeItem(LOCAL_STORAGE_KEYS.MATCH_SCORES);
    localStorage.removeItem(LOCAL_STORAGE_KEYS.MATCH_SESSION);
    setState({
      sessionId: null,
      matchScores: new Map(),
      isLoading: false,
    });
  }, []);

  const getMatchPercentage = useCallback((jobId: string): number | undefined => {
    return state.matchScores.get(jobId);
  }, [state.matchScores]);

  return {
    ...state,
    saveMatches,
    clearMatches,
    getMatchPercentage,
  };
}
