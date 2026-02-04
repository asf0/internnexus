"use client";

import { useState, useTransition } from "react";
import { matchResume } from "../app/actions/match";
import { Building2, MapPin, TrendingUp } from "lucide-react";

interface MatchResponse {
  matches: Array<{
    job_id: string;
    score: number;
    match_percentage: number;
    title: string;
    company: string;
    location: string;
  }>;
  total: number;
  error?: string;
}

export default function ResumeUploader() {
  const [result, setResult] = useState<MatchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const handleSubmit = (formData: FormData) => {
    setError(null);
    startTransition(async () => {
      const response = (await matchResume(formData)) as MatchResponse;
      if (response.error) {
        setError(response.error);
        setResult(null);
      } else {
        setResult(response);
      }
    });
  };

  const getMatchColor = (percentage: number) => {
    if (percentage >= 80) return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300";
    if (percentage >= 60) return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300";
    if (percentage >= 40) return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300";
    return "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300";
  };

  return (
    <div className="space-y-4">
      <form
        className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900"
        action={handleSubmit}
      >
        <div className="flex flex-col gap-3">
          <label className="text-sm font-medium text-slate-700 dark:text-slate-300">Upload Resume (PDF or TXT)</label>
          <input
            name="resume"
            type="file"
            accept=".pdf,.txt"
            className="rounded-md border border-slate-200 bg-white p-2 text-sm text-slate-900 file:mr-4 file:rounded file:border-0 file:bg-slate-100 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-slate-700 hover:file:bg-slate-200 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100 dark:file:bg-slate-700 dark:file:text-slate-300 dark:hover:file:bg-slate-600"
          />
          <button
            type="submit"
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
            disabled={isPending}
          >
            {isPending ? "Matching..." : "Find Matches"}
          </button>
          {error && (
            <div className="rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
              {error}
            </div>
          )}
        </div>
      </form>

      {result && result.matches.length > 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              Found {result.total} matching job{result.total !== 1 ? "s" : ""}
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400">Ranked by match percentage</p>
          </div>
          <div className="space-y-3">
            {result.matches.map((match) => (
              <div
                key={match.job_id}
                className="flex items-center justify-between rounded-xl border border-slate-200 p-4 hover:border-slate-300 dark:border-slate-700 dark:hover:border-slate-600"
              >
                <div className="flex-1">
                  <h4 className="font-semibold text-slate-900 dark:text-slate-100">{match.title}</h4>
                  <div className="mt-1 flex flex-wrap gap-3 text-sm text-slate-600 dark:text-slate-400">
                    <span className="flex items-center gap-1">
                      <Building2 className="h-4 w-4" />
                      {match.company}
                    </span>
                    <span className="flex items-center gap-1">
                      <MapPin className="h-4 w-4" />
                      {match.location}
                    </span>
                  </div>
                </div>
                <div className={`ml-4 rounded-lg px-4 py-2 text-right font-semibold ${getMatchColor(match.match_percentage)}`}>
                  <div className="flex items-center gap-1">
                    <TrendingUp className="h-4 w-4" />
                    {match.match_percentage.toFixed(1)}%
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {result && result.matches.length === 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="text-center text-slate-600 dark:text-slate-400">No matches found. Try adjusting filters or uploading a different resume.</p>
        </div>
      )}
    </div>
  );
}
