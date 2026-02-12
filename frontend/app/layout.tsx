import "./globals.css";
import type { ReactNode } from "react";
import AuthProvider from "../components/AuthProvider";
import Footer from "../components/Footer";

export const metadata = {
  title: "InternNexus",
  description: "Internship discovery and matching platform"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning={true}>
      <head />
      <body className="min-h-screen bg-slate-50 text-slate-900 dark:bg-md-surface dark:text-md-on-surface flex flex-col" suppressHydrationWarning={true}>
        <AuthProvider>
          <main className="flex-1 mx-auto w-full max-w-(--breakpoint-2xl) px-4 py-8 sm:px-6 lg:px-8">{children}</main>
          <Footer />
        </AuthProvider>
      </body>
    </html>
  );
}
