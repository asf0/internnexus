'use client';

import { Button } from '@/components/ui';
import type { MatchResponse } from '@/lib/types/job';

interface ResumePanelProps {
  readonly isOpen: boolean;
  readonly isMatching: boolean;
  readonly isMatched: boolean;
  readonly matchResult: MatchResponse | null;
  readonly onProfileResumeMatch: () => void;
  readonly onResumeFormSubmit: (event: React.FormEvent<HTMLFormElement>) => void;
  readonly onClearMatches: () => void;
}

export function ResumePanel({
  isOpen,
  isMatching,
  isMatched,
  matchResult,
  onProfileResumeMatch,
  onResumeFormSubmit,
  onClearMatches,
}: ResumePanelProps) {
  if (!isOpen) return null;

  return (
    <div className="dark:border-md-outline-variant dark:bg-md-surface-container-low rounded-xl border border-slate-200 bg-white p-4">
      <div className="mb-4">
        <label className="dark:text-md-on-surface-variant mb-1.5 block text-sm font-medium text-slate-700">
          Match using your saved profile resume
        </label>
        <Button type="button" disabled={isMatching} onClick={onProfileResumeMatch}>
          {isMatching ? 'Matching...' : 'Find Matches (Saved Resume)'}
        </Button>
      </div>
      <div className="dark:text-md-on-surface-variant mb-3 text-xs text-slate-500">
        Or upload a different file for a one-time match:
      </div>
      <form onSubmit={onResumeFormSubmit} className="flex flex-wrap items-end gap-4">
        <div className="min-w-[200px] flex-1">
          <label className="dark:text-md-on-surface-variant mb-1.5 block text-sm font-medium text-slate-700">
            Upload resume (one-time override)
          </label>
          <input
            name="resume"
            type="file"
            accept="application/pdf"
            className="dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface w-full rounded-lg border border-slate-200 bg-white p-2 text-sm text-slate-900 file:mr-3 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-slate-700 hover:file:bg-slate-200 dark:file:bg-slate-700 dark:file:text-slate-300"
          />
        </div>
        <Button type="submit" disabled={isMatching}>
          {isMatching ? 'Matching...' : 'Find Matches'}
        </Button>
        {isMatched && (
          <Button type="button" variant="secondary" onClick={onClearMatches}>
            Clear Matches
          </Button>
        )}
      </form>
      {matchResult && !isMatching && (
        <div className="dark:text-md-on-surface-variant mt-3 text-sm text-slate-600">
          {matchResult.error
            ? matchResult.error
            : matchResult.total > 0
              ? matchResult.reused_from_cache
                ? `Matched ${matchResult.total} job${matchResult.total === 1 ? '' : 's'} (reused your previous resume results).`
                : `Matched ${matchResult.total} job${matchResult.total === 1 ? '' : 's'}.`
              : 'No matches found.'}
        </div>
      )}
    </div>
  );
}
