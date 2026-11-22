import {
  fetchNotifications,
  fetchSavedJobs,
  fetchUserResume,
  getUserProfile,
} from '@/app/actions/user';
import { auth } from '@/auth';
import { User, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { redirect } from 'next/navigation';
import ProfileExtras from '@/components/profile/ProfileExtras';
import { toSafeHttpUrl } from '@/lib/utils';

export default async function ProfilePage() {
  const session = await auth();

  if (!session?.user) {
    redirect('/');
  }

  const profile = await getUserProfile();
  const [resumeResult, notifications, savedJobs] = await Promise.all([
    fetchUserResume(),
    fetchNotifications(),
    fetchSavedJobs(),
  ]);
  const resume = resumeResult.data;

  if (!profile) {
    return (
      <div className="text-center">
        <p className="text-foreground-secondary">Failed to load profile. Please try again.</p>
      </div>
    );
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };
  const professionalDetails = [
    { label: 'Job title', value: profile.job_title },
    { label: 'Company', value: profile.company },
    { label: 'Industry', value: profile.industry },
    { label: 'Phone', value: profile.phone },
  ].filter((item): item is { label: string; value: string } => !!item.value);
  const safeLinkedInUrl = toSafeHttpUrl(profile.linkedin_url);
  const safePortfolioUrl = toSafeHttpUrl(profile.portfolio_url);

  return (
    <div className="px-4 py-8">
      <div className="mx-auto max-w-7xl">
        {/* Back Button */}
        <Link
          href="/"
          className="text-foreground-secondary hover:text-foreground mb-6 inline-flex items-center gap-2 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back</span>
        </Link>

        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-foreground text-3xl font-bold">My Profile</h1>
            <p className="text-foreground-secondary mt-1">View your profile information</p>
          </div>
          <Link
            href="/settings"
            className="bg-accent text-on-accent hover:bg-accent-hover rounded-lg px-4 py-2 text-sm font-medium transition-colors"
          >
            Edit Profile
          </Link>
        </div>

        {/* Two Column Layout */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Left Column - Profile Card */}
          <div className="lg:col-span-1">
            <div className="border-border bg-surface sticky top-8 overflow-hidden rounded-xl border shadow-sm">
              {/* Avatar and Basic Info */}
              <div className="border-border border-b p-6 text-center">
                {profile.image ? (
                  <img
                    src={profile.image}
                    alt={profile.name || 'User'}
                    className="border-border mx-auto mb-4 h-24 w-24 rounded-full border-2 object-cover"
                  />
                ) : (
                  <div className="border-border bg-foreground mx-auto mb-4 flex h-24 w-24 items-center justify-center rounded-full border-2">
                    <User className="text-canvas h-12 w-12" />
                  </div>
                )}

                <h2 className="text-foreground text-2xl font-bold">
                  {profile.name || 'Anonymous User'}
                </h2>
                <div className="text-foreground-secondary mt-2 space-y-1 text-sm">
                  <p>{profile.email}</p>
                  {profile.location && <p>{profile.location}</p>}
                </div>
                <p className="text-foreground-muted mt-3 text-sm">
                  Member since {formatDate(profile.created_at)}
                </p>
              </div>

              {/* Quick Stats */}
              <div className="p-4">
                <div className="grid grid-cols-2 gap-4 text-center">
                  <div className="bg-surface-subtle rounded-lg p-3">
                    <p className="text-foreground text-2xl font-semibold">
                      {profile.skills.length}
                    </p>
                    <p className="text-foreground-muted text-xs">Skills</p>
                  </div>
                  <div className="bg-surface-subtle rounded-lg p-3">
                    <p className="text-foreground text-2xl font-semibold">
                      {profile.preferred_locations.length}
                    </p>
                    <p className="text-foreground-muted text-xs">Locations</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column - Details */}
          <div className="space-y-6 lg:col-span-2">
            {/* Bio */}
            {profile.bio && (
              <div className="border-border bg-surface rounded-xl border p-6 shadow-sm">
                <h3 className="text-foreground mb-3 text-lg font-semibold">About</h3>
                <p className="text-foreground-secondary whitespace-pre-wrap">{profile.bio}</p>
              </div>
            )}

            {/* Professional Info */}
            <div className="border-border bg-surface rounded-xl border p-6 shadow-sm">
              <h3 className="text-foreground mb-4 text-lg font-semibold">
                Professional Information
              </h3>

              {professionalDetails.length > 0 && (
                <div className="border-border bg-border grid grid-cols-1 gap-px overflow-hidden rounded-lg border sm:grid-cols-2">
                  {professionalDetails.map((item) => (
                    <div key={item.label} className="bg-surface px-4 py-3">
                      <p className="text-foreground-muted text-xs font-medium">{item.label}</p>
                      <p className="text-foreground mt-1 text-sm font-medium">{item.value}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Skills */}
              {profile.skills.length > 0 && (
                <div className="mt-6">
                  <p className="text-foreground-muted mb-2 text-sm">Skills</p>
                  <div className="flex flex-wrap gap-2">
                    {profile.skills.map((skill) => (
                      <span
                        key={skill}
                        className="bg-surface-subtle text-foreground-secondary rounded-full px-3 py-1 text-sm"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Preferred Locations */}
              {profile.preferred_locations.length > 0 && (
                <div className="mt-6">
                  <p className="text-foreground-muted mb-2 text-sm">Preferred Job Locations</p>
                  <div className="flex flex-wrap gap-2">
                    {profile.preferred_locations.map((loc) => (
                      <span
                        key={loc}
                        className="border-border text-foreground-secondary rounded-full border px-3 py-1 text-sm"
                      >
                        {loc}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Links */}
            {(safeLinkedInUrl || safePortfolioUrl) && (
              <div className="border-border bg-surface rounded-xl border p-6 shadow-sm">
                <h3 className="text-foreground mb-4 text-lg font-semibold">Links</h3>

                <div className="space-y-3">
                  {safeLinkedInUrl && (
                    <a
                      href={safeLinkedInUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-foreground decoration-border text-sm font-medium underline underline-offset-4"
                    >
                      <span>LinkedIn Profile</span>
                    </a>
                  )}

                  {safePortfolioUrl && (
                    <a
                      href={safePortfolioUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-foreground decoration-border text-sm font-medium underline underline-offset-4"
                    >
                      <span>Portfolio / Website</span>
                    </a>
                  )}
                </div>
              </div>
            )}

            {/* Empty State */}
            {!profile.bio &&
              !profile.job_title &&
              !profile.company &&
              !profile.industry &&
              profile.skills.length === 0 &&
              !safeLinkedInUrl &&
              !safePortfolioUrl && (
                <div className="border-border bg-surface rounded-xl border p-6 text-center shadow-sm">
                  <p className="text-foreground-muted">No additional profile information yet.</p>
                  <Link
                    href="/settings"
                    className="text-foreground decoration-border mt-2 inline-block text-sm font-medium underline underline-offset-4"
                  >
                    Complete your profile →
                  </Link>
                </div>
              )}

            <ProfileExtras
              initialResume={resume}
              resumeLoadError={resumeResult.error}
              initialNotifications={notifications}
              initialSavedJobs={savedJobs}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
