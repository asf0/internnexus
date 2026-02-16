import { useState, useCallback, useEffect } from "react";
import { LOCAL_STORAGE_KEYS } from "@/lib/constants";
import type { MatchResult } from "@/lib/types/job";

interface MatchState {
  matchIds: string[];
  matchScores: Map<string, number>;
  isLoading: boolean;
}

export function useMatchState() {
  const [state, setState] = useState<MatchState>({
    matchIds: [],
    matchScores: new Map(),
    isLoading: true,
  });

  useEffect(() => {
    const storedIds = localStorage.getItem(LOCAL_STORAGE_KEYS.MATCH_IDS);
    const storedScores = localStorage.getItem(LOCAL_STORAGE_KEYS.MATCH_SCORES);

    const matchIds: string[] = storedIds ? JSON.parse(storedIds) : [];
    const scores: Record<string, number> = storedScores ? JSON.parse(storedScores) : {};

    setState({
      matchIds,
      matchScores: new Map(Object.entries(scores)),
      isLoading: false,
    });
  }, []);

  const saveMatches = useCallback((matches: MatchResult[]) => {
    const matchIds = matches.map((match) => match.job_id).filter(Boolean);
    const scoresMap: Record<string, number> = {};
    matches.forEach((match) => {
      scoresMap[match.job_id] = match.match_percentage;
    });

    localStorage.setItem(LOCAL_STORAGE_KEYS.MATCH_SCORES, JSON.stringify(scoresMap));
    localStorage.setItem(LOCAL_STORAGE_KEYS.MATCH_IDS, JSON.stringify(matchIds));

    setState({
      matchIds,
      matchScores: new Map(Object.entries(scoresMap)),
      isLoading: false,
    });

    return matchIds;
  }, []);

  const clearMatches = useCallback(() => {
    localStorage.removeItem(LOCAL_STORAGE_KEYS.MATCH_SCORES);
    localStorage.removeItem(LOCAL_STORAGE_KEYS.MATCH_IDS);
    setState({
      matchIds: [],
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
