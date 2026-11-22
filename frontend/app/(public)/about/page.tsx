import type { Metadata } from 'next';
import Link from 'next/link';
import { AboutContent } from '@/components/modals/AboutModal';
import { BASE_URL } from '@/lib/config';
import { siteOpenGraphImage } from '@/lib/seo';

export const metadata: Metadata = {
  title: 'About',
  description: 'Learn how InternNexus helps people discover and organize job opportunities.',
  alternates: {
    canonical: `${BASE_URL}/about`,
  },
  openGraph: {
    title: 'About InternNexus',
    description: 'Learn how InternNexus helps people discover and organize job opportunities.',
    url: `${BASE_URL}/about`,
    images: siteOpenGraphImage(),
  },
  twitter: {
    card: 'summary_large_image',
    title: 'About InternNexus',
    description: 'Learn how InternNexus helps people discover and organize job opportunities.',
    images: siteOpenGraphImage(),
  },
};

export default function AboutPage() {
  return (
    <article className="mx-auto max-w-3xl">
      <Link
        href="/"
        className="text-foreground-secondary decoration-border hover:text-foreground text-sm font-medium underline underline-offset-4"
      >
        Back to job search
      </Link>
      <h1 className="text-foreground mt-6 mb-8 text-3xl font-semibold tracking-tight">
        About InternNexus
      </h1>
      <AboutContent />
    </article>
  );
}
