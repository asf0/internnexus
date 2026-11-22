'use client';

import { Button } from '@/components/ui';
import type { MatchResponse } from '@/lib/types/job';

interface ResumePanelProps {
  readonly isOpen: boolean;
  readonly isMatching: boolean;
  readonly isMatched: boolean;
  readonly matchResult: MatchResponse | null;
  readonly onProfileResumeMatch: () => void;
  readonly onResumeFormSubmit: (event: React.SyntheticEvent<HTMLFormElement, SubmitEvent>) => void;
  readonly onClearMatches: () => void;
}

function getMatchResultMessage(result: MatchResponse): string {
  if (result.error) return result.error;
  if (result.total === 0) return 'No matches found.';

  const plural = result.total === 1 ? '' : 's';
  const cacheNote = result.reused_from_cache ? ' (reused your previous resume results).' : '.';
  return `Matched ${result.total} job${plural}${cacheNote}`;
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
    <div className="border-border bg-surface rounded-xl border p-4">
      <div className="mb-4">
        <p className="text-foreground-secondary mb-1.5 block text-sm font-medium">
          Match using your saved profile resume
        </p>
        <Button type="button" disabled={isMatching} onClick={onProfileResumeMatch}>
          {isMatching ? 'Matching...' : 'Find Matches (Saved Resume)'}
        </Button>
      </div>
      <div className="text-foreground-muted mb-3 text-xs">
        Or upload a different file for a one-time match:
      </div>
      <form onSubmit={onResumeFormSubmit} className="flex flex-wrap items-end gap-4">
        <div className="min-w-[200px] flex-1">
          <label
            htmlFor="resume-match-upload"
            className="text-foreground-secondary mb-1.5 block text-sm font-medium"
          >
            Upload resume (one-time override)
          </label>
          <input
            id="resume-match-upload"
            name="resume"
            type="file"
            accept="application/pdf"
            className="border-border bg-surface text-foreground file:bg-surface-subtle file:text-foreground-secondary hover:file:bg-surface-raised w-full rounded-lg border p-2 text-sm file:mr-3 file:rounded-md file:border-0 file:px-3 file:py-1.5 file:text-sm file:font-medium"
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
        <div className="text-foreground-secondary mt-3 text-sm">
          {getMatchResultMessage(matchResult)}
        </div>
      )}
    </div>
  );
}
