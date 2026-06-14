import { getUserProfile } from '@/app/actions/user';
import { fetchNotifications, fetchSavedJobs, fetchUserResume } from '@/app/actions/user';
import { auth } from '@/auth';
import {
  User,
  Mail,
  MapPin,
  Briefcase,
  Building,
  GraduationCap,
  Link as LinkIcon,
  Calendar,
  ArrowLeft,
} from 'lucide-react';
import Link from 'next/link';
import { redirect } from 'next/navigation';
import ProfileExtras from '@/components/profile/ProfileExtras';

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
        <p className="dark:text-md-on-surface-variant text-slate-600">
          Failed to load profile. Please try again.
        </p>
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

  return (
    <div className="px-4 py-8">
      <div className="mx-auto max-w-7xl">
        {/* Back Button */}
        <Link
          href="/"
          className="dark:text-md-on-surface-variant mb-6 inline-flex items-center gap-2 text-slate-600 transition-colors hover:text-slate-900 dark:hover:text-slate-100"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back</span>
        </Link>

        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="dark:text-md-on-surface text-3xl font-bold text-slate-900">
              My Profile
            </h1>
            <p className="dark:text-md-on-surface-variant mt-1 text-slate-600">
              View your profile information
            </p>
          </div>
          <Link
            href="/settings"
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
          >
            Edit Profile
          </Link>
        </div>

        {/* Two Column Layout */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Left Column - Profile Card */}
          <div className="lg:col-span-1">
            <div className="dark:bg-md-surface-container dark:border-md-outline-variant sticky top-8 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
              {/* Avatar and Basic Info */}
              <div className="dark:border-md-outline-variant border-b border-slate-200 p-6 text-center">
                {profile.image ? (
                  <img
                    src={profile.image}
                    alt={profile.name || 'User'}
                    className="dark:border-md-outline-variant mx-auto mb-4 h-32 w-32 rounded-full border-4 border-slate-100 object-cover"
                  />
                ) : (
                  <div className="dark:border-md-outline-variant mx-auto mb-4 flex h-32 w-32 items-center justify-center rounded-full border-4 border-slate-100 bg-blue-600">
                    <User className="h-16 w-16 text-white" />
                  </div>
                )}

                <h2 className="dark:text-md-on-surface text-2xl font-bold text-slate-900">
                  {profile.name || 'Anonymous User'}
                </h2>
                <div className="dark:text-md-on-surface-variant mt-2 flex flex-col items-center gap-1 text-slate-600">
                  <div className="flex items-center gap-1">
                    <Mail className="h-4 w-4" />
                    <span className="text-sm">{profile.email}</span>
                  </div>
                  {profile.location && (
                    <div className="flex items-center gap-1">
                      <MapPin className="h-4 w-4" />
                      <span className="text-sm">{profile.location}</span>
                    </div>
                  )}
                </div>
                <div className="dark:text-md-on-surface-variant mt-3 flex items-center justify-center gap-1 text-slate-500">
                  <Calendar className="h-4 w-4" />
                  <span className="text-sm">Member since {formatDate(profile.created_at)}</span>
                </div>
              </div>

              {/* Quick Stats */}
              <div className="p-4">
                <div className="grid grid-cols-2 gap-4 text-center">
                  <div className="dark:bg-md-surface-container-high/50 rounded-lg bg-slate-50 p-3">
                    <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                      {profile.skills.length}
                    </p>
                    <p className="dark:text-md-on-surface-variant text-xs text-slate-500">Skills</p>
                  </div>
                  <div className="dark:bg-md-surface-container-high/50 rounded-lg bg-slate-50 p-3">
                    <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                      {profile.preferred_locations.length}
                    </p>
                    <p className="dark:text-md-on-surface-variant text-xs text-slate-500">
                      Locations
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column - Details */}
          <div className="space-y-6 lg:col-span-2">
            {/* Bio */}
            {profile.bio && (
              <div className="dark:bg-md-surface-container dark:border-md-outline-variant rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <h3 className="dark:text-md-on-surface mb-3 text-lg font-semibold text-slate-900">
                  About
                </h3>
                <p className="dark:text-md-on-surface-variant whitespace-pre-wrap text-slate-600">
                  {profile.bio}
                </p>
              </div>
            )}

            {/* Professional Info */}
            <div className="dark:bg-md-surface-container dark:border-md-outline-variant rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <h3 className="dark:text-md-on-surface mb-4 text-lg font-semibold text-slate-900">
                Professional Information
              </h3>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {profile.job_title && (
                  <div className="flex items-start gap-3">
                    <div className="rounded-lg bg-blue-100 p-2 dark:bg-blue-900/30">
                      <Briefcase className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                    </div>
                    <div>
                      <p className="dark:text-md-on-surface-variant text-sm text-slate-500">
                        Job Title
                      </p>
                      <p className="dark:text-md-on-surface font-medium text-slate-900">
                        {profile.job_title}
                      </p>
                    </div>
                  </div>
                )}

                {profile.company && (
                  <div className="flex items-start gap-3">
                    <div className="rounded-lg bg-green-100 p-2 dark:bg-green-900/30">
                      <Building className="h-5 w-5 text-green-600 dark:text-green-400" />
                    </div>
                    <div>
                      <p className="dark:text-md-on-surface-variant text-sm text-slate-500">
                        Company
                      </p>
                      <p className="dark:text-md-on-surface font-medium text-slate-900">
                        {profile.company}
                      </p>
                    </div>
                  </div>
                )}

                {profile.industry && (
                  <div className="flex items-start gap-3">
                    <div className="rounded-lg bg-purple-100 p-2 dark:bg-purple-900/30">
                      <GraduationCap className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                    </div>
                    <div>
                      <p className="dark:text-md-on-surface-variant text-sm text-slate-500">
                        Industry
                      </p>
                      <p className="dark:text-md-on-surface font-medium text-slate-900">
                        {profile.industry}
                      </p>
                    </div>
                  </div>
                )}

                {profile.phone && (
                  <div className="flex items-start gap-3">
                    <div className="rounded-lg bg-orange-100 p-2 dark:bg-orange-900/30">
                      <Mail className="h-5 w-5 text-orange-600 dark:text-orange-400" />
                    </div>
                    <div>
                      <p className="dark:text-md-on-surface-variant text-sm text-slate-500">
                        Phone
                      </p>
                      <p className="dark:text-md-on-surface font-medium text-slate-900">
                        {profile.phone}
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* Skills */}
              {profile.skills.length > 0 && (
                <div className="mt-6">
                  <p className="dark:text-md-on-surface-variant mb-2 text-sm text-slate-500">
                    Skills
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {profile.skills.map((skill) => (
                      <span
                        key={skill}
                        className="dark:bg-md-surface-container-high dark:text-md-on-surface-variant rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700"
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
                  <p className="dark:text-md-on-surface-variant mb-2 text-sm text-slate-500">
                    Preferred Job Locations
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {profile.preferred_locations.map((loc) => (
                      <span
                        key={loc}
                        className="rounded-full bg-blue-50 px-3 py-1 text-sm text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
                      >
                        {loc}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Links */}
            {(profile.linkedin_url || profile.portfolio_url) && (
              <div className="dark:bg-md-surface-container dark:border-md-outline-variant rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <h3 className="dark:text-md-on-surface mb-4 text-lg font-semibold text-slate-900">
                  Links
                </h3>

                <div className="space-y-3">
                  {profile.linkedin_url && (
                    <a
                      href={profile.linkedin_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-3 text-blue-600 hover:underline dark:text-blue-400"
                    >
                      <LinkIcon className="h-5 w-5" />
                      <span>LinkedIn Profile</span>
                    </a>
                  )}

                  {profile.portfolio_url && (
                    <a
                      href={profile.portfolio_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-3 text-blue-600 hover:underline dark:text-blue-400"
                    >
                      <LinkIcon className="h-5 w-5" />
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
              !profile.linkedin_url &&
              !profile.portfolio_url && (
                <div className="dark:bg-md-surface-container dark:border-md-outline-variant rounded-xl border border-slate-200 bg-white p-6 text-center shadow-sm">
                  <p className="dark:text-md-on-surface-variant text-slate-500">
                    No additional profile information yet.
                  </p>
                  <Link
                    href="/settings"
                    className="mt-2 inline-block text-blue-600 hover:underline dark:text-blue-400"
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
