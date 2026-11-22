import './globals.css';
import type { Metadata, Viewport } from 'next';
import type { ReactNode } from 'react';
import Script from 'next/script';
import { Providers } from '@/components/common';
import { BASE_URL } from '@/lib/config';
import { SITE_DESCRIPTION, SITE_NAME, siteOpenGraphImage } from '@/lib/seo';

export const metadata: Metadata = {
  metadataBase: new URL(BASE_URL),
  title: {
    default: 'InternNexus — Search Internships & Entry-Level Jobs',
    template: '%s | InternNexus',
  },
  description: SITE_DESCRIPTION,
  applicationName: SITE_NAME,
  authors: [{ name: 'asf0' }],
  creator: 'asf0',
  keywords: [
    'internships',
    'entry level jobs',
    'job search',
    'new grad jobs',
    'remote internships',
    'career opportunities',
  ],
  openGraph: {
    type: 'website',
    siteName: SITE_NAME,
    locale: 'en_US',
    url: BASE_URL,
    title: 'InternNexus — Search Internships & Entry-Level Jobs',
    description: SITE_DESCRIPTION,
    images: siteOpenGraphImage(),
  },
  twitter: {
    card: 'summary_large_image',
    title: 'InternNexus — Search Internships & Entry-Level Jobs',
    description: SITE_DESCRIPTION,
    images: siteOpenGraphImage(),
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-image-preview': 'large',
      'max-snippet': -1,
      'max-video-preview': -1,
    },
  },
};

export const viewport: Viewport = {
  themeColor: '#2563eb',
  width: 'device-width',
  initialScale: 1,
};

const ADSENSE_CLIENT = process.env.NEXT_PUBLIC_ADSENSE_CLIENT ?? 'ca-pub-3648058884929802';

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning={true}>
      <body className="bg-canvas text-foreground min-h-screen antialiased" suppressHydrationWarning>
        <Script
          id="adsbygoogle-init"
          strategy="afterInteractive"
          src={`https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${ADSENSE_CLIENT}`}
          crossOrigin="anonymous"
        />
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
