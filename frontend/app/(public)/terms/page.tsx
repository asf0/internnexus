import type { Metadata } from 'next';
import Link from 'next/link';
import { TermsContent } from '@/components/modals/TermsModal';
import { BASE_URL } from '@/lib/config';
import { siteOpenGraphImage } from '@/lib/seo';

export const metadata: Metadata = {
  title: 'Terms of Service',
  description: 'Terms governing the use of InternNexus.',
  alternates: {
    canonical: `${BASE_URL}/terms`,
  },
  openGraph: {
    title: 'Terms of Service | InternNexus',
    description: 'Terms governing the use of InternNexus.',
    url: `${BASE_URL}/terms`,
    images: siteOpenGraphImage(),
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Terms of Service | InternNexus',
    description: 'Terms governing the use of InternNexus.',
    images: siteOpenGraphImage(),
  },
};

export default function TermsPage() {
  return (
    <article className="mx-auto max-w-3xl">
      <Link
        href="/"
        className="text-foreground-secondary decoration-border hover:text-foreground text-sm font-medium underline underline-offset-4"
      >
        Back to job search
      </Link>
      <h1 className="text-foreground mt-6 mb-8 text-3xl font-semibold tracking-tight">
        Terms of Service
      </h1>
      <TermsContent />
    </article>
  );
}
