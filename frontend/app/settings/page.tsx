import { auth } from '@/auth';
import { redirect } from 'next/navigation';
import { getUserProfile } from '@/app/actions/user';
import { SettingsForm } from '@/components/settings';

export default async function SettingsPage() {
  const session = await auth();

  if (!session?.user) {
    redirect('/');
  }

  const profile = await getUserProfile();

  if (!profile) {
    return (
      <div className="dark:bg-md-surface-container-low flex min-h-screen items-center justify-center bg-slate-50">
        <p className="dark:text-md-on-surface-variant text-slate-600">
          Failed to load profile. Please try again.
        </p>
      </div>
    );
  }

  return <SettingsForm profile={profile} />;
}
