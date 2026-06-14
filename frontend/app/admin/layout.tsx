import { redirect } from 'next/navigation';
import { auth } from '@/auth';
import { getBackendToken } from '@/lib/auth.server';
import { BACKEND_URL } from '@/lib/config';
import { createAuthHeaders } from '@/lib/http';
import AdminLayoutClient from './AdminLayoutClient';

/**
 * Verify if the current user has admin access by calling the admin endpoint.
 */
async function verifyAdminAccess(): Promise<boolean> {
  try {
    const backendToken = await getBackendToken();
    if (!backendToken) {
      return false;
    }

    const response = await fetch(`${BACKEND_URL}/admin/jobs`, {
      method: 'GET',
      headers: createAuthHeaders(backendToken),
    });

    return response.ok;
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
