function JobCardSkeleton() {
  return (
    <div className="border-border bg-surface animate-pulse rounded-xl border p-5">
      <div className="bg-border h-5 w-2/3 rounded" />
      <div className="bg-surface-subtle mt-3 h-4 w-1/3 rounded" />
      <div className="mt-4 flex gap-2">
        <div className="bg-surface-subtle h-6 w-24 rounded-full" />
        <div className="bg-surface-subtle h-6 w-20 rounded-full" />
      </div>
    </div>
  );
}

export default function HomeLoading() {
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Loading jobs">
      <div className="flex animate-pulse items-center justify-between">
        <div>
          <div className="bg-border h-7 w-36 rounded" />
          <div className="bg-surface-subtle mt-2 h-4 w-64 rounded" />
        </div>
        <div className="bg-surface-subtle h-9 w-20 rounded" />
      </div>
      <div className="bg-border h-11 animate-pulse rounded-lg" />
      <div className="space-y-3">
        {Array.from({ length: 5 }, (_, index) => (
          <JobCardSkeleton key={index} />
        ))}
      </div>
      <span className="sr-only">Loading job opportunities…</span>
    </div>
  );
}
