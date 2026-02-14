import type { Metadata } from "next";
import DOMPurify from "isomorphic-dompurify";
import { ExternalLink, Calendar, Globe, GraduationCap, Flag, Flame } from "lucide-react";
import { fetchJob } from "../../../lib/api";
import { BASE_URL } from "../../../lib/config";
import { Badge, Button } from "../../../components/ui";
import { CATEGORY_LABEL_MAP } from "../../../lib/constants";

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
    "employmentType": "INTERN",
    "directApply": true,
    "url": `${BASE_URL}/jobs/${job.id}`,
  };

  return (
    <div className="space-y-6">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      
      <header className="space-y-2">
        <div className="flex items-center gap-2">
          <p className="text-sm font-semibold uppercase text-slate-500 dark:text-md-on-surface-variant">
            {job.company}
          </p>
          {job.is_faang_plus && (
            <Badge variant="faang" icon={Flame}>FAANG+</Badge>
          )}
        </div>
        <h1 className="text-3xl font-semibold text-slate-900 dark:text-md-on-surface">{job.title}</h1>
        <p className="text-sm text-slate-600 dark:text-md-on-surface-variant">{job.location}</p>
        
        <div className="flex flex-wrap gap-2 pt-2">
          {job.job_category && (
            <Badge variant="default">
              {CATEGORY_LABEL_MAP[job.job_category] || job.job_category}
            </Badge>
          )}
          {job.visa_sponsored && (
            <Badge variant="visa" icon={Globe}>Visa Sponsored</Badge>
          )}
          {job.f1_friendly && (
            <Badge variant="f1" icon={GraduationCap}>F1 Friendly</Badge>
          )}
          {job.requires_us_citizenship && (
            <Badge variant="danger" icon={Flag}>US Citizenship Required</Badge>
          )}
          {job.requires_advanced_degree && (
            <Badge variant="purple" icon={GraduationCap}>Advanced Degree</Badge>
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

      {job.apply_url && !job.application_closed ? (
        <a
          href={job.apply_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-3 font-medium text-white transition-colors hover:bg-blue-700"
        >
          Apply Now
          <ExternalLink className="h-4 w-4" />
        </a>
      ) : job.application_closed ? (
        <div className="inline-flex items-center gap-2 rounded-lg bg-slate-200 px-6 py-3 font-medium text-slate-500 dark:bg-md-surface-container-high dark:text-md-on-surface-variant">
          Application Closed
        </div>
      ) : null}
    </div>
  );
}
