import type { Metadata } from "next";
import DOMPurify from "isomorphic-dompurify";
import { Calendar } from "lucide-react";
import { fetchJob } from "../../../lib/api";
import { BASE_URL } from "../../../lib/config";
import { Badge } from "../../../components/ui";
import { ApplyNowAuthButton } from "../../../components/jobs";
import { JOB_TYPE_LABEL_MAP, WORK_MODE_LABEL_MAP } from "../../../lib/constants";
import { formatCategoryLabel } from "../../../lib/utils";
import { auth } from "@/auth";
import { headers } from "next/headers";
import { toSafeJsonLd } from "@/lib/security/jsonld";

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
  const nonce = (await headers()).get("x-nonce") ?? undefined;
  const job = await fetchJob(id);
  const session = await auth();
  const isAuthenticated = !!session?.user;

  if (!job) {
    return <p>Job not found.</p>;
  }

  const cleanDescription = job.description_text.replace(/<[^>]*>/g, "");

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "JobPosting",
    "title": job.title,
    "hiringOrganization": {
      "@type": "Organization",
      "name": job.company,
    },
    "jobLocation": {
      "@type": "Place",
      "address": {
        "@type": "PostalAddress",
        "addressLocality": job.city || job.location,
        "addressRegion": job.state,
        "addressCountry": job.country || "US",
      },
    },
    "datePosted": job.posted_at,
    "description": cleanDescription,
    "employmentType": job.job_type?.toUpperCase() || "INTERN",
    "directApply": true,
    "url": `${BASE_URL}/jobs/${job.id}`,
  };

  return (
    <div className="space-y-6">
      <script
        suppressHydrationWarning
        nonce={nonce}
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: toSafeJsonLd(jsonLd) }}
      />

      <header className="space-y-2">
        <p className="text-sm font-semibold uppercase text-slate-500 dark:text-md-on-surface-variant">
          {job.company}
        </p>
        <h1 className="text-3xl font-semibold text-slate-900 dark:text-md-on-surface">{job.title}</h1>
        <p className="text-sm text-slate-600 dark:text-md-on-surface-variant">{job.location}</p>

        <div className="flex flex-wrap gap-2 pt-2">
          {job.job_category && (
            <Badge variant="default">
              {formatCategoryLabel(job.job_category)}
            </Badge>
          )}
          {job.job_type && (
            <Badge variant="info">
              {JOB_TYPE_LABEL_MAP[job.job_type] || job.job_type}
            </Badge>
          )}
          {job.work_mode && (
            <Badge variant="success">
              {WORK_MODE_LABEL_MAP[job.work_mode] || job.work_mode}
            </Badge>
          )}
        </div>

        {job.posted_at && (
          <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-md-on-surface-variant pt-2">
            <Calendar className="h-4 w-4" />
            <span>Posted {new Date(job.posted_at).toLocaleDateString()}</span>
          </div>
        )}
      </header>

      <article
        className="prose max-w-none prose-headings:text-slate-900 prose-p:text-slate-700 prose-li:text-slate-700 prose-strong:text-slate-900 dark:prose-invert dark:prose-headings:text-md-on-surface dark:prose-p:text-md-on-surface-variant dark:prose-li:text-md-on-surface-variant dark:prose-strong:text-md-on-surface"
        dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(job.description_text) }}
      />

      {job.apply_url && (
        <ApplyNowAuthButton jobId={job.id} applyUrl={job.apply_url} isAuthenticated={isAuthenticated} />
      )}
    </div>
  );
}
