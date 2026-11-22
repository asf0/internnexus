import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { BASE_URL } from '@/lib/config';
import { siteOpenGraphImage } from '@/lib/seo';
import { fetchPublicJobDetail, fetchRelatedJobs } from '@/lib/public-job-detail';
import { Badge } from '@/components/ui';
import { ApplyButtonWithSession, RelatedJobs } from '@/components/jobs';
import { JOB_TYPE_LABEL_MAP, WORK_MODE_LABEL_MAP } from '@/lib/constants';
import { formatCategoryLabel } from '@/lib/utils';
import { headers } from 'next/headers';
import { toSafeJsonLd } from '@/lib/security/jsonld';
import { cache } from 'react';
import { jobPostingEmploymentType, jobPostingValidThrough } from '@/lib/job-posting-schema';
import { companySlug, categorySlug } from '@/lib/hub-slugs';

interface JobPageProps {
  params: Promise<{ id: string }>;
}

// This deduplicates the metadata and page fetch during a single render. The
// tagged fetch beneath it retains successful public responses across requests.
const getJob = cache(fetchPublicJobDetail);
const getRelated = cache(fetchRelatedJobs);

function stripHtmlTags(value: string): string {
  let plainText = '';
  let insideTag = false;
  for (const character of value) {
    if (character === '<') insideTag = true;
    else if (character === '>') insideTag = false;
    else if (!insideTag) plainText += character;
  }
  return plainText;
}

export async function generateMetadata({ params }: JobPageProps): Promise<Metadata> {
  const { id } = await params;
  const job = await getJob(id);
  if (!job) {
    return {
      title: 'Job not found',
      description: 'This listing is no longer available.',
    };
  }

  // Strip HTML tags for plain text meta description
  const cleanDescription = stripHtmlTags(job.description_html);

  return {
    title: `${job.title} at ${job.company}`,
    description: cleanDescription.slice(0, 140),
    alternates: {
      canonical: `${BASE_URL}/jobs/${id}`,
    },
    openGraph: {
      type: 'article',
      url: `${BASE_URL}/jobs/${id}`,
      title: `${job.title} at ${job.company}`,
      description: cleanDescription.slice(0, 140),
      images: siteOpenGraphImage(),
    },
    twitter: {
      card: 'summary_large_image',
      title: `${job.title} at ${job.company}`,
      description: cleanDescription.slice(0, 140),
      images: siteOpenGraphImage(),
    },
  };
}

export default async function JobDetailPage({ params }: Readonly<JobPageProps>) {
  const { id } = await params;
  const nonce = (await headers()).get('x-nonce') ?? undefined;
  const job = await getJob(id);

  if (!job) {
    notFound();
  }

  const related = await getRelated(id);

  const cleanDescription = stripHtmlTags(job.description_html);

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'JobPosting',
    title: job.title,
    hiringOrganization: {
      '@type': 'Organization',
      name: job.company,
    },
    jobLocation: {
      '@type': 'Place',
      address: {
        '@type': 'PostalAddress',
        addressLocality: job.city || job.location,
        addressRegion: job.state,
        addressCountry: job.country || 'US',
      },
    },
    datePosted: job.posted_at,
    validThrough: jobPostingValidThrough(job.posted_at),
    description: cleanDescription,
    employmentType: jobPostingEmploymentType(job.job_type),
    identifier: {
      '@type': 'PropertyValue',
      name: job.source,
      value: job.id,
    },
    directApply: true,
    url: `${BASE_URL}/jobs/${job.id}`,
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <script
        suppressHydrationWarning
        nonce={nonce}
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: toSafeJsonLd(jsonLd) }}
      />

      <nav aria-label="Breadcrumb" className="text-sm">
        <ol className="flex flex-wrap items-center gap-1">
          <li>
            <Link
              href="/"
              className="text-foreground-secondary hover:text-foreground underline-offset-4 hover:underline"
            >
              Jobs
            </Link>
          </li>
          <li aria-hidden="true" className="text-foreground-muted">
            /
          </li>
          <li>
            <Link
              href={`/companies/${companySlug(job.company)}`}
              className="text-foreground-secondary hover:text-foreground underline-offset-4 hover:underline"
            >
              {job.company}
            </Link>
          </li>
          {job.job_category && (
            <>
              <li aria-hidden="true" className="text-foreground-muted">
                /
              </li>
              <li>
                <Link
                  href={`/categories/${categorySlug(job.job_category)}`}
                  className="text-foreground-secondary hover:text-foreground underline-offset-4 hover:underline"
                >
                  {formatCategoryLabel(job.job_category)}
                </Link>
              </li>
            </>
          )}
        </ol>
      </nav>

      <header className="border-border space-y-2 border-b pb-6">
        <p className="text-foreground-muted text-sm font-semibold uppercase">{job.company}</p>
        <h1 className="text-foreground text-3xl font-semibold">{job.title}</h1>
        <p className="text-foreground-secondary text-sm">{job.location}</p>

        <div className="flex flex-wrap gap-2 pt-2">
          {job.job_category && (
            <Badge variant="outline">{formatCategoryLabel(job.job_category)}</Badge>
          )}
          {job.job_type && (
            <Badge variant="outline">{JOB_TYPE_LABEL_MAP[job.job_type] || job.job_type}</Badge>
          )}
          {job.work_mode && (
            <Badge variant="outline">{WORK_MODE_LABEL_MAP[job.work_mode] || job.work_mode}</Badge>
          )}
        </div>

        {job.posted_at && (
          <time dateTime={job.posted_at} className="text-foreground-muted block pt-2 text-sm">
            Posted{' '}
            {new Date(job.posted_at).toLocaleDateString('en-US', {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            })}
          </time>
        )}

        {job.apply_url && (
          <div className="pt-4">
            <ApplyButtonWithSession jobId={job.id} applyUrl={job.apply_url} />
          </div>
        )}
      </header>

      <article
        className="prose prose-headings:text-slate-900 prose-p:text-slate-700 prose-li:text-slate-700 prose-strong:text-slate-900 dark:prose-invert dark:prose-headings:text-md-on-surface dark:prose-p:text-md-on-surface-variant dark:prose-li:text-md-on-surface-variant dark:prose-strong:text-md-on-surface max-w-none"
        dangerouslySetInnerHTML={{ __html: job.description_html }}
      />

      <RelatedJobs company={job.company} category={job.job_category} jobs={related} />
    </div>
  );
}
