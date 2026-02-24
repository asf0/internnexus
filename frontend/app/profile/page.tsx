import { getUserProfile } from "@/app/actions/user"
import { fetchNotifications, fetchSavedJobs, fetchUserResume } from "@/app/actions/user"
import { auth } from "@/auth"
import { User, Mail, MapPin, Briefcase, Building, GraduationCap, Link as LinkIcon, Calendar, ArrowLeft } from "lucide-react"
import Link from "next/link"
import { redirect } from "next/navigation"
import ProfileExtras from "@/components/profile/ProfileExtras"

export default async function ProfilePage() {
  const session = await auth()

  if (!session?.user) {
    redirect("/")
  }

  const profile = await getUserProfile()
  const [resumeResult, notifications, savedJobs] = await Promise.all([
    fetchUserResume(),
    fetchNotifications(),
    fetchSavedJobs(),
  ])
  const resume = resumeResult.data

  if (!profile) {
    return (
        <div className="text-center">
          <p className="text-slate-600 dark:text-md-on-surface-variant">Failed to load profile. Please try again.</p>
        </div>
    )
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    })
  }

  return (
    <div className="py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Back Button */}
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-slate-600 dark:text-md-on-surface-variant hover:text-slate-900 dark:hover:text-slate-100 transition-colors mb-6"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back</span>
        </Link>

        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 dark:text-md-on-surface">My Profile</h1>
            <p className="mt-1 text-slate-600 dark:text-md-on-surface-variant">View your profile information</p>
          </div>
          <Link
            href="/settings"
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
          >
            Edit Profile
          </Link>
        </div>

        {/* Two Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Profile Card */}
          <div className="lg:col-span-1">
            <div className="bg-white dark:bg-md-surface-container rounded-xl shadow-sm border border-slate-200 dark:border-md-outline-variant overflow-hidden sticky top-8">
              {/* Avatar and Basic Info */}
              <div className="p-6 text-center border-b border-slate-200 dark:border-md-outline-variant">
                {profile.image ? (
                  <img
                    src={profile.image}
                    alt={profile.name || "User"}
                    className="h-32 w-32 rounded-full object-cover border-4 border-slate-100 dark:border-md-outline-variant mx-auto mb-4"
                  />
                ) : (
                  <div className="h-32 w-32 rounded-full bg-blue-600 flex items-center justify-center border-4 border-slate-100 dark:border-md-outline-variant mx-auto mb-4">
                    <User className="h-16 w-16 text-white" />
                  </div>
                )}

                <h2 className="text-2xl font-bold text-slate-900 dark:text-md-on-surface">
                  {profile.name || "Anonymous User"}
                </h2>
                <div className="mt-2 flex flex-col items-center gap-1 text-slate-600 dark:text-md-on-surface-variant">
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
                <div className="mt-3 flex items-center justify-center gap-1 text-slate-500 dark:text-md-on-surface-variant">
                  <Calendar className="h-4 w-4" />
                  <span className="text-sm">Member since {formatDate(profile.created_at)}</span>
                </div>
              </div>

              {/* Quick Stats */}
              <div className="p-4">
                <div className="grid grid-cols-2 gap-4 text-center">
                  <div className="p-3 bg-slate-50 dark:bg-md-surface-container-high/50 rounded-lg">
                    <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">{profile.skills.length}</p>
                    <p className="text-xs text-slate-500 dark:text-md-on-surface-variant">Skills</p>
                  </div>
                  <div className="p-3 bg-slate-50 dark:bg-md-surface-container-high/50 rounded-lg">
                    <p className="text-2xl font-bold text-green-600 dark:text-green-400">{profile.preferred_locations.length}</p>
                    <p className="text-xs text-slate-500 dark:text-md-on-surface-variant">Locations</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column - Details */}
          <div className="lg:col-span-2 space-y-6">
            {/* Bio */}
            {profile.bio && (
              <div className="bg-white dark:bg-md-surface-container rounded-xl shadow-sm border border-slate-200 dark:border-md-outline-variant p-6">
                <h3 className="text-lg font-semibold text-slate-900 dark:text-md-on-surface mb-3">About</h3>
                <p className="text-slate-600 dark:text-md-on-surface-variant whitespace-pre-wrap">{profile.bio}</p>
              </div>
            )}

            {/* Professional Info */}
            <div className="bg-white dark:bg-md-surface-container rounded-xl shadow-sm border border-slate-200 dark:border-md-outline-variant p-6">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-md-on-surface mb-4">Professional Information</h3>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {profile.job_title && (
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                      <Briefcase className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                    </div>
                    <div>
                      <p className="text-sm text-slate-500 dark:text-md-on-surface-variant">Job Title</p>
                      <p className="font-medium text-slate-900 dark:text-md-on-surface">{profile.job_title}</p>
                    </div>
                  </div>
                )}

                {profile.company && (
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
                      <Building className="h-5 w-5 text-green-600 dark:text-green-400" />
                    </div>
                    <div>
                      <p className="text-sm text-slate-500 dark:text-md-on-surface-variant">Company</p>
                      <p className="font-medium text-slate-900 dark:text-md-on-surface">{profile.company}</p>
                    </div>
                  </div>
                )}

                {profile.industry && (
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
                      <GraduationCap className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                    </div>
                    <div>
                      <p className="text-sm text-slate-500 dark:text-md-on-surface-variant">Industry</p>
                      <p className="font-medium text-slate-900 dark:text-md-on-surface">{profile.industry}</p>
                    </div>
                  </div>
                )}

                {profile.phone && (
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-orange-100 dark:bg-orange-900/30 rounded-lg">
                      <Mail className="h-5 w-5 text-orange-600 dark:text-orange-400" />
                    </div>
                    <div>
                      <p className="text-sm text-slate-500 dark:text-md-on-surface-variant">Phone</p>
                      <p className="font-medium text-slate-900 dark:text-md-on-surface">{profile.phone}</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Skills */}
              {profile.skills.length > 0 && (
                <div className="mt-6">
                  <p className="text-sm text-slate-500 dark:text-md-on-surface-variant mb-2">Skills</p>
                  <div className="flex flex-wrap gap-2">
                    {profile.skills.map((skill) => (
                      <span
                        key={skill}
                        className="px-3 py-1 bg-slate-100 dark:bg-md-surface-container-high text-slate-700 dark:text-md-on-surface-variant rounded-full text-sm"
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
                  <p className="text-sm text-slate-500 dark:text-md-on-surface-variant mb-2">Preferred Job Locations</p>
                  <div className="flex flex-wrap gap-2">
                    {profile.preferred_locations.map((loc) => (
                      <span
                        key={loc}
                        className="px-3 py-1 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full text-sm"
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
              <div className="bg-white dark:bg-md-surface-container rounded-xl shadow-sm border border-slate-200 dark:border-md-outline-variant p-6">
                <h3 className="text-lg font-semibold text-slate-900 dark:text-md-on-surface mb-4">Links</h3>

                <div className="space-y-3">
                  {profile.linkedin_url && (
                    <a
                      href={profile.linkedin_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-3 text-blue-600 dark:text-blue-400 hover:underline"
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
                      className="flex items-center gap-3 text-blue-600 dark:text-blue-400 hover:underline"
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
                <div className="bg-white dark:bg-md-surface-container rounded-xl shadow-sm border border-slate-200 dark:border-md-outline-variant p-6 text-center">
                  <p className="text-slate-500 dark:text-md-on-surface-variant">No additional profile information yet.</p>
                  <Link
                    href="/settings"
                    className="mt-2 inline-block text-blue-600 dark:text-blue-400 hover:underline"
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
  )
}
