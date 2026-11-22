import type { Metadata } from 'next';
import Link from 'next/link';
import { PrivacyContent } from '@/components/modals/PrivacyModal';
import { BASE_URL } from '@/lib/config';
import { siteOpenGraphImage } from '@/lib/seo';

export const metadata: Metadata = {
  title: 'Privacy Policy',
  description: 'How InternNexus collects, uses, and protects information.',
  alternates: {
    canonical: `${BASE_URL}/privacy`,
  },
  openGraph: {
    title: 'Privacy Policy | InternNexus',
    description: 'How InternNexus collects, uses, and protects information.',
    url: `${BASE_URL}/privacy`,
    images: siteOpenGraphImage(),
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Privacy Policy | InternNexus',
    description: 'How InternNexus collects, uses, and protects information.',
    images: siteOpenGraphImage(),
  },
};

export default function PrivacyPage() {
  return (
    <article className="mx-auto max-w-3xl">
      <Link
        href="/"
        className="text-foreground-secondary decoration-border hover:text-foreground text-sm font-medium underline underline-offset-4"
      >
        Back to job search
      </Link>
      <h1 className="text-foreground mt-6 mb-8 text-3xl font-semibold tracking-tight">
        Privacy Policy
      </h1>
      <PrivacyContent />
    </article>
  );
}
