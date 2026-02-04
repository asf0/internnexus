import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "InternNexus",
  description: "Internship discovery and matching platform"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100" suppressHydrationWarning={true}>
        <main className="mx-auto w-full max-w-screen-2xl px-4 py-8 sm:px-6 lg:px-8">{children}</main>
      </body>
    </html>
  );
}
