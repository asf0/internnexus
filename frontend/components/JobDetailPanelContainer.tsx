import JobDetailPanel from "./JobDetailPanel";
import type { Job } from "../lib/types";

interface JobDetailPanelContainerProps {
  job: Job | null;
  isLoading?: boolean;
  onClose: () => void;
}

export function JobDetailPanelContainer({ 
  job, 
  isLoading = false, 
  onClose 
}: JobDetailPanelContainerProps) {
  if (!job && !isLoading) {
    return null;
  }

  return (
    <>
      {/* Mobile: Full-screen modal overlay */}
      <div 
        className="fixed inset-0 z-40 bg-black/50 lg:hidden" 
        onClick={onClose} 
      />
      <div className="fixed inset-4 z-50 flex lg:hidden">
        <div className="w-full rounded-2xl bg-white dark:bg-md-surface-container-low">
          <JobDetailPanel job={job} isLoading={isLoading} onClose={onClose} />
        </div>
      </div>

      {/* Desktop: Sticky side panel */}
      <div className="hidden sticky top-4 h-[calc(100vh-6rem)] w-1/2 min-w-[400px] lg:block">
        <JobDetailPanel job={job} isLoading={isLoading} onClose={onClose} />
      </div>
    </>
  );
}
