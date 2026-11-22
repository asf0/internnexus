import Link from 'next/link';

export default function JobNotFound() {
  return (
    <div className="mx-auto flex min-h-[50vh] max-w-lg flex-col items-center justify-center text-center">
      <p className="text-foreground text-xl font-semibold">This job is no longer available</p>
      <p className="text-foreground-secondary mt-2 text-sm leading-6">
        The employer may have closed or removed the listing. Return to search to find current
        opportunities.
      </p>
      <Link
        href="/"
        className="border-border bg-surface text-foreground hover:bg-surface-subtle focus-visible:ring-focus-ring mt-6 rounded-lg border px-4 py-2 text-sm font-medium focus-visible:ring-2 focus-visible:outline-none"
      >
        Browse current jobs
      </Link>
    </div>
  );
}
