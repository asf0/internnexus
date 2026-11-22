import type { ReactNode } from 'react';
import { Footer } from '@/components/common';

export default function PublicLayout({ children }: { readonly children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <main className="mx-auto w-full max-w-(--breakpoint-2xl) flex-1 px-4 py-8 sm:px-6 lg:px-8">
        {children}
      </main>
      <Footer />
    </div>
  );
}
