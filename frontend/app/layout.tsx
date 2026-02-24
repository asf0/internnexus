import "./globals.css";
import type { ReactNode } from "react";
import { Footer } from "@/components/common";

export const metadata = {
  title: "InternNexus",
  description: "job discovery and matching platform"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning={true}>
      <head>
        <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-3648058884929802"
     crossOrigin="anonymous"></script>
      </head>
      <body className="min-h-screen bg-slate-50 text-slate-900 dark:bg-md-surface dark:text-md-on-surface flex flex-col" suppressHydrationWarning={true}>
        <main className="flex-1 mx-auto w-full max-w-(--breakpoint-2xl) px-4 py-8 sm:px-6 lg:px-8">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
