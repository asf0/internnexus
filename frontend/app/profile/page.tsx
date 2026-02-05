import { getUserProfile } from "@/app/actions/user"
import { auth } from "@/auth"
import { User, Mail, MapPin, Briefcase, Building, GraduationCap, Link as LinkIcon, Calendar, ArrowLeft } from "lucide-react"
import Link from "next/link"
import { redirect } from "next/navigation"

export default async function ProfilePage() {
  const session = await auth()

  if (!session?.user) {
    redirect("/login")
  }

  const profile = await getUserProfile()

  if (!profile) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900">
        <div className="text-center">
          <p className="text-slate-600 dark:text-slate-400">Failed to load profile. Please try again.</p>
        </div>
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
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Back Button */}
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 transition-colors mb-6"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back</span>
        </Link>

        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">My Profile</h1>
            <p className="mt-1 text-slate-600 dark:text-slate-400">View your profile information</p>
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
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden sticky top-8">
              {/* Avatar and Basic Info */}
              <div className="p-6 text-center border-b border-slate-200 dark:border-slate-700">
                {profile.image ? (
                  <img
                    src={profile.image}
                    alt={profile.name || "User"}
                    className="h-32 w-32 rounded-full object-cover border-4 border-slate-100 dark:border-slate-700 mx-auto mb-4"
                  />
                ) : (
                  <div className="h-32 w-32 rounded-full bg-blue-600 flex items-center justify-center border-4 border-slate-100 dark:border-slate-700 mx-auto mb-4">
                    <User className="h-16 w-16 text-white" />
                  </div>
                )}

                <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                  {profile.name || "Anonymous User"}
                </h2>
                <div className="mt-2 flex flex-col items-center gap-1 text-slate-600 dark:text-slate-400">
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
                <div className="mt-3 flex items-center justify-center gap-1 text-slate-500 dark:text-slate-500">
                  <Calendar className="h-4 w-4" />
                  <span className="text-sm">Member since {formatDate(profile.created_at)}</span>
                </div>
              </div>

              {/* Quick Stats */}
              <div className="p-4">
                <div className="grid grid-cols-2 gap-4 text-center">
                  <div className="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                    <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">{profile.skills.length}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">Skills</p>
                  </div>
                  <div className="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                    <p className="text-2xl font-bold text-green-600 dark:text-green-400">{profile.preferred_locations.length}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">Locations</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column - Details */}
          <div className="lg:col-span-2 space-y-6">
            {/* Bio */}
            {profile.bio && (
              <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
                <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-3">About</h3>
                <p className="text-slate-600 dark:text-slate-400 whitespace-pre-wrap">{profile.bio}</p>
              </div>
            )}

            {/* Professional Info */}
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">Professional Information</h3>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {profile.job_title && (
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                      <Briefcase className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                    </div>
                    <div>
                      <p className="text-sm text-slate-500 dark:text-slate-400">Job Title</p>
                      <p className="font-medium text-slate-900 dark:text-slate-100">{profile.job_title}</p>
                    </div>
                  </div>
                )}

                {profile.company && (
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
                      <Building className="h-5 w-5 text-green-600 dark:text-green-400" />
                    </div>
                    <div>
                      <p className="text-sm text-slate-500 dark:text-slate-400">Company</p>
                      <p className="font-medium text-slate-900 dark:text-slate-100">{profile.company}</p>
                    </div>
                  </div>
                )}

                {profile.industry && (
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
                      <GraduationCap className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                    </div>
                    <div>
                      <p className="text-sm text-slate-500 dark:text-slate-400">Industry</p>
                      <p className="font-medium text-slate-900 dark:text-slate-100">{profile.industry}</p>
                    </div>
                  </div>
                )}

                {profile.phone && (
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-orange-100 dark:bg-orange-900/30 rounded-lg">
                      <Mail className="h-5 w-5 text-orange-600 dark:text-orange-400" />
                    </div>
                    <div>
                      <p className="text-sm text-slate-500 dark:text-slate-400">Phone</p>
                      <p className="font-medium text-slate-900 dark:text-slate-100">{profile.phone}</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Skills */}
              {profile.skills.length > 0 && (
                <div className="mt-6">
                  <p className="text-sm text-slate-500 dark:text-slate-400 mb-2">Skills</p>
                  <div className="flex flex-wrap gap-2">
                    {profile.skills.map((skill) => (
                      <span
                        key={skill}
                        className="px-3 py-1 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-full text-sm"
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
                  <p className="text-sm text-slate-500 dark:text-slate-400 mb-2">Preferred Job Locations</p>
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
              <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
                <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">Links</h3>

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
                <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6 text-center">
                  <p className="text-slate-500 dark:text-slate-400">No additional profile information yet.</p>
                  <Link
                    href="/settings"
                    className="mt-2 inline-block text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    Complete your profile →
                  </Link>
                </div>
              )}
          </div>
        </div>
      </div>
    </div>
  )
}
