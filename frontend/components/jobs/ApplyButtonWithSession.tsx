'use client';

import { useSession } from 'next-auth/react';
import ApplyNowAuthButton from './ApplyNowAuthButton';

interface ApplyButtonWithSessionProps {
  readonly jobId: string;
  readonly applyUrl: string;
}

/**
 * Resolves authentication client-side so the server render of the job page
 * stays free of per-request `auth()` calls. The page HTML itself carries no
 * session state, which keeps renders cacheable and avoids the streaming
 * shells that read as soft 404s when the backend hiccups.
 */
export default function ApplyButtonWithSession({ jobId, applyUrl }: ApplyButtonWithSessionProps) {
  const { status } = useSession();
  const isAuthenticated = status === 'authenticated';

  return <ApplyNowAuthButton jobId={jobId} applyUrl={applyUrl} isAuthenticated={isAuthenticated} />;
}
