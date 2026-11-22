import { redirect } from 'next/navigation';
import type { Metadata } from 'next';
import { auth } from '@/auth';
import { requestBackend } from '@/lib/api.server';
import AdminLayoutClient from './AdminLayoutClient';

// Defense in depth alongside the robots.txt disallow: authenticated admin
// pages should never be indexed even if a crawler reaches one.
export const metadata: Metadata = {
  robots: { index: false, follow: false },
};

/**
 * Verify if the current user has admin access by calling the admin endpoint.
 */
async function verifyAdminAccess(): Promise<boolean> {
  try {
    const result = await requestBackend('/admin/jobs');
    return !result.failure;
  } catch {
    return false;
  }
}

export default async function AdminLayout({ children }: { readonly children: React.ReactNode }) {
  const session = await auth();

  if (!session?.user) {
    redirect('/?auth=required&callbackUrl=/admin');
  }

  const isAdmin = await verifyAdminAccess();

  return (
    <AdminLayoutClient
      user={{
        id: session.user.id,
        name: session.user.name,
        email: session.user.email,
        image: session.user.image,
      }}
      isAdmin={isAdmin}
    >
      {children}
    </AdminLayoutClient>
  );
}
