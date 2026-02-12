import type { Metadata } from "next";
import DOMPurify from "isomorphic-dompurify";
import { fetchJob } from "../../../lib/api";

interface JobPageProps {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: JobPageProps): Promise<Metadata> {
  const { id } = await params;
  const job = await fetchJob(id);
  if (!job) {
    return {
      title: "Job not found | InternNexus",
      description: "This listing is no longer available.",
    };
  }

  // Strip HTML tags for plain text meta description
  const cleanDescription = job.description_text.replace(/<[^>]*>/g, "");

  return {
    title: `${job.title} at ${job.company} | InternNexus`,
    description: cleanDescription.slice(0, 140),
    openGraph: {
      title: `${job.title} at ${job.company}`,
      description: cleanDescription.slice(0, 140),
    },
  };
}

export default async function JobDetailPage({ params }: JobPageProps) {
  const { id } = await params;
  const job = await fetchJob(id);

  if (!job) {
    return <p>Job not found.</p>;
  }

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <p className="text-sm font-semibold uppercase text-slate-500 dark:text-md-on-surface-variant">{job.company}</p>
        <h1 className="text-3xl font-semibold text-slate-900 dark:text-md-on-surface">{job.title}</h1>
        <p className="text-sm text-slate-600 dark:text-md-on-surface-variant">{job.location}</p>
        <div className="flex gap-2 text-xs">
          {job.visa_sponsored !== null && (
            <span className="rounded-full bg-emerald-100 px-3 py-1 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300">
              Visa Sponsored
            </span>
          )}
          {job.f1_friendly !== null && (
            <span className="rounded-full bg-blue-100 px-3 py-1 text-blue-700 dark:bg-blue-900 dark:text-blue-300">
              F1 Friendly
            </span>
          )}
        </div>
      </header>

      <article
        className="prose max-w-none prose-headings:text-slate-900 prose-p:text-slate-700 prose-li:text-slate-700 prose-strong:text-slate-900 dark:prose-invert dark:prose-headings:text-md-on-surface dark:prose-p:text-md-on-surface-variant dark:prose-li:text-md-on-surface-variant dark:prose-strong:text-md-on-surface"
        dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(job.description_text) }}
      />

      <a
        href={job.apply_url}
        className="inline-flex items-center rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 dark:bg-md-on-surface dark:text-md-surface dark:hover:bg-md-on-surface-variant"
      >
        Apply Now
      </a>
    </div>
  );
}