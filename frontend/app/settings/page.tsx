"use client"

import { useState, useEffect } from "react"
import { useSession } from "next-auth/react"
import { useRouter } from "next/navigation"
import {
  User,
  Briefcase,
  Building,
  MapPin,
  Phone,
  Link as LinkIcon,
  GraduationCap,
  Lock,
  Trash2,
  AlertTriangle,
  Plus,
  X,
  Save,
  Loader2,
  ArrowLeft,
} from "lucide-react"
import { getUserProfile, updateUserProfile, changePassword, deleteAccount } from "@/app/actions/user"
import PasswordInput, { calculateStrength } from "@/components/PasswordInput"
import Modal from "@/components/Modal"
import { Button, Input, Card, CardContent, Badge, IconContainer, Alert, FormField } from "@/components/ui"

interface UserProfile {
  id: string
  email: string
  name: string | null
  image: string | null
  bio: string | null
  phone: string | null
  location: string | null
  job_title: string | null
  company: string | null
  industry: string | null
  skills: string[]
  linkedin_url: string | null
  portfolio_url: string | null
  preferred_locations: string[]
  has_password: boolean
}

export default function SettingsPage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null)

  // Form states
  const [personalForm, setPersonalForm] = useState({
    name: "",
    bio: "",
    phone: "",
    location: "",
  })

  const [professionalForm, setProfessionalForm] = useState({
    job_title: "",
    company: "",
    industry: "",
    linkedin_url: "",
    portfolio_url: "",
  })

  const [skills, setSkills] = useState<string[]>([])
  const [newSkill, setNewSkill] = useState("")
  const [preferredLocations, setPreferredLocations] = useState<string[]>([])
  const [newLocation, setNewLocation] = useState("")

  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  })

  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [deleteConfirmText, setDeleteConfirmText] = useState("")

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/")
      return
    }

    if (status === "authenticated") {
      loadProfile()
    }
  }, [status, router])

  const loadProfile = async () => {
    const data = await getUserProfile()
    if (data) {
      setProfile(data)
      setPersonalForm({
        name: data.name || "",
        bio: data.bio || "",
        phone: data.phone || "",
        location: data.location || "",
      })
      setProfessionalForm({
        job_title: data.job_title || "",
        company: data.company || "",
        industry: data.industry || "",
        linkedin_url: data.linkedin_url || "",
        portfolio_url: data.portfolio_url || "",
      })
      setSkills(data.skills || [])
      setPreferredLocations(data.preferred_locations || [])
    }
    setIsLoading(false)
  }

  const handleSaveAll = async () => {
    setIsSaving(true)
    setMessage(null)

    // Validate password if being changed
    if (passwordForm.new_password) {
      if (passwordForm.new_password !== passwordForm.confirm_password) {
        setMessage({ type: "error", text: "New passwords do not match" })
        setIsSaving(false)
        return
      }

      const strength = calculateStrength(passwordForm.new_password)
      if (strength.score < 100) {
        setMessage({ type: "error", text: "Password does not meet all requirements" })
        setIsSaving(false)
        return
      }

      // Check if new password is same as current password
      if (passwordForm.new_password === passwordForm.current_password) {
        setMessage({ type: "error", text: "New password cannot be the same as current password" })
        setIsSaving(false)
        return
      }
    }

    // Save profile information
    const profileResult = await updateUserProfile({
      name: personalForm.name || null,
      bio: personalForm.bio || null,
      phone: personalForm.phone || null,
      location: personalForm.location || null,
      job_title: professionalForm.job_title || null,
      company: professionalForm.company || null,
      industry: professionalForm.industry || null,
      linkedin_url: professionalForm.linkedin_url || null,
      portfolio_url: professionalForm.portfolio_url || null,
      skills,
      preferred_locations: preferredLocations,
    })

    if (!profileResult.success) {
      setMessage({ type: "error", text: profileResult.error || "Failed to save profile changes" })
      setIsSaving(false)
      return
    }

    // Save password if provided
    if (passwordForm.current_password) {
      const passwordResult = await changePassword({
        current_password: passwordForm.current_password,  // Now TypeScript knows it's string
        new_password: passwordForm.new_password,
      })

      if (!passwordResult.success) {
        setMessage({ type: "error", text: passwordResult.error || "Failed to change password" })
        setIsSaving(false)
        return
      }

      // Clear password form on success
      setPasswordForm({ current_password: "", new_password: "", confirm_password: "" })
    }

    setMessage({ type: "success", text: "All changes saved successfully!" })
    loadProfile()
    setIsSaving(false)
  }

  const handleDeleteAccount = async () => {
    if (deleteConfirmText !== "DELETE") {
      setMessage({ type: "error", text: 'Please type "DELETE" to confirm' })
      return
    }

    setIsSaving(true)
    const result = await deleteAccount()

    if (result.success) {
      router.push("/")
      router.refresh()
    } else {
      setMessage({ type: "error", text: result.error || "Failed to delete account" })
      setIsSaving(false)
    }
  }

  const addSkill = () => {
    if (newSkill.trim() && !skills.includes(newSkill.trim())) {
      setSkills([...skills, newSkill.trim()])
      setNewSkill("")
    }
  }

  const removeSkill = (skill: string) => {
    setSkills(skills.filter((s) => s !== skill))
  }

  const addLocation = () => {
    if (newLocation.trim() && !preferredLocations.includes(newLocation.trim())) {
      setPreferredLocations([...preferredLocations, newLocation.trim()])
      setNewLocation("")
    }
  }

  const removeLocation = (location: string) => {
    setPreferredLocations(preferredLocations.filter((l) => l !== location))
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-md-surface-container-low">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    )
  }

  return (
    <div className="py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Back Button */}
        <Button
          variant="ghost"
          onClick={() => router.back()}
          className="mb-6"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </Button>

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 dark:text-md-on-surface">Account Settings</h1>
          <p className="mt-1 text-slate-600 dark:text-md-on-surface-variant">Manage your profile and account preferences</p>
        </div>

        {/* Message */}
        {message && (
          <Alert type={message.type} className="mb-6">
            {message.text}
          </Alert>
        )}

        {/* Two Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Personal & Password */}
          <div className="lg:col-span-1 space-y-6">
            {/* Personal Information */}
            <Card>
              <CardContent>
                <div className="flex items-center gap-3 mb-6">
                  <IconContainer icon={User} color="blue" />
                  <div>
                    <h2 className="text-xl font-semibold text-slate-900 dark:text-md-on-surface">Personal</h2>
                    <p className="text-sm text-slate-500 dark:text-md-on-surface-variant">Your basic info</p>
                  </div>
                </div>

                <div className="space-y-4">
                  <FormField
                    label="Full Name"
                    value={personalForm.name}
                    onChange={(value) => setPersonalForm({ ...personalForm, name: value })}
                    placeholder="John Doe"
                  />

                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-md-on-surface-variant mb-1">Bio / About</label>
                    <textarea
                      value={personalForm.bio}
                      onChange={(e) => setPersonalForm({ ...personalForm, bio: e.target.value })}
                      rows={3}
                      className="w-full px-3 py-2 border border-slate-300 dark:border-md-outline-variant rounded-lg focus:ring-2 focus:ring-md-primary focus:border-md-primary dark:bg-md-surface-container-high dark:text-md-on-surface"
                      placeholder="Tell us about yourself..."
                    />
                  </div>

                  <FormField
                    label="Phone"
                    value={personalForm.phone}
                    onChange={(value) => setPersonalForm({ ...personalForm, phone: value })}
                    icon={Phone}
                    placeholder="+1 (555) 123-4567"
                  />

                  <FormField
                    label="Location"
                    value={personalForm.location}
                    onChange={(value) => setPersonalForm({ ...personalForm, location: value })}
                    icon={MapPin}
                    placeholder="San Francisco, CA"
                  />
                </div>
              </CardContent>
            </Card>

            {/* Password */}
            <Card>
              <CardContent>
                <div className="flex items-center gap-3 mb-6">
                  <IconContainer icon={Lock} color="purple" />
                  <div>
                    <h2 className="text-xl font-semibold text-slate-900 dark:text-md-on-surface">Password</h2>
                    <p className="text-sm text-slate-500 dark:text-md-on-surface-variant">
                      {profile?.has_password ? "Change password" : "Set password"}
                    </p>
                  </div>
                </div>

                <div className="space-y-4">
                  {profile?.has_password && (
                    <FormField
                      label="Current Password"
                      value={passwordForm.current_password}
                      onChange={(value) => setPasswordForm({ ...passwordForm, current_password: value })}
                      type="password"
                    />
                  )}

                  <PasswordInput
                    value={passwordForm.new_password}
                    onChange={(value) => setPasswordForm({ ...passwordForm, new_password: value })}
                    confirmValue={passwordForm.confirm_password}
                    onConfirmChange={(value) => setPasswordForm({ ...passwordForm, confirm_password: value })}
                    showConfirmation={true}
                    label="New Password"
                    id="new-password"
                  />
                </div>
              </CardContent>
            </Card>
          </div>

            {/* Right Column - Professional & Danger Zone */}
          <div className="lg:col-span-2 space-y-6">
            {/* Professional Information */}
            <Card>
              <CardContent>
                <div className="flex items-center gap-3 mb-6">
                  <IconContainer icon={Briefcase} color="green" />
                  <div>
                    <h2 className="text-xl font-semibold text-slate-900 dark:text-md-on-surface">Professional Information</h2>
                    <p className="text-sm text-slate-500 dark:text-md-on-surface-variant">Your work details</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <FormField
                    label="Job Title"
                    value={professionalForm.job_title}
                    onChange={(value) => setProfessionalForm({ ...professionalForm, job_title: value })}
                    icon={Briefcase}
                    placeholder="Software Engineer"
                  />

                  <FormField
                    label="Company"
                    value={professionalForm.company}
                    onChange={(value) => setProfessionalForm({ ...professionalForm, company: value })}
                    icon={Building}
                    placeholder="Acme Inc."
                  />

                  <FormField
                    label="Industry"
                    value={professionalForm.industry}
                    onChange={(value) => setProfessionalForm({ ...professionalForm, industry: value })}
                    icon={GraduationCap}
                    placeholder="Technology"
                  />

                  <FormField
                    label="LinkedIn URL"
                    value={professionalForm.linkedin_url}
                    onChange={(value) => setProfessionalForm({ ...professionalForm, linkedin_url: value })}
                    icon={LinkIcon}
                    placeholder="https://linkedin.com/in/username"
                  />

                  <div className="md:col-span-2">
                    <FormField
                      label="Portfolio / Website"
                      value={professionalForm.portfolio_url}
                      onChange={(value) => setProfessionalForm({ ...professionalForm, portfolio_url: value })}
                      icon={LinkIcon}
                      placeholder="https://yourportfolio.com"
                    />
                  </div>
                </div>

                {/* Skills */}
                <div className="mt-6">
                  <label className="block text-sm font-medium text-slate-700 dark:text-md-on-surface-variant mb-2">Skills</label>
                  <div className="flex flex-wrap gap-2 mb-2">
                    {skills.map((skill) => (
                      <Badge key={skill} variant="visa">
                        {skill}
                        <button
                          onClick={() => removeSkill(skill)}
                          className="ml-1 hover:text-blue-900 dark:hover:text-blue-100"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </Badge>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <Input
                      type="text"
                      value={newSkill}
                      onChange={(e) => setNewSkill(e.target.value)}
                      onKeyPress={(e) => e.key === "Enter" && (e.preventDefault(), addSkill())}
                      placeholder="Add a skill (e.g., Python, React)"
                      className="flex-1"
                    />
                    <Button variant="secondary" size="sm" onClick={addSkill}>
                      <Plus className="h-5 w-5" />
                    </Button>
                  </div>
                </div>

                {/* Preferred Locations */}
                <div className="mt-6">
                  <label className="block text-sm font-medium text-slate-700 dark:text-md-on-surface-variant mb-2">Preferred Job Locations</label>
                  <div className="flex flex-wrap gap-2 mb-2">
                    {preferredLocations.map((location) => (
                      <Badge key={location} variant="f1">
                        {location}
                        <button
                          onClick={() => removeLocation(location)}
                          className="ml-1 hover:text-green-900 dark:hover:text-green-100"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </Badge>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <Input
                      type="text"
                      value={newLocation}
                      onChange={(e) => setNewLocation(e.target.value)}
                      onKeyPress={(e) => e.key === "Enter" && (e.preventDefault(), addLocation())}
                      placeholder="Add a location (e.g., San Francisco, Remote)"
                      className="flex-1"
                    />
                    <Button variant="secondary" size="sm" onClick={addLocation}>
                      <Plus className="h-5 w-5" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Danger Zone */}
            <div className="bg-red-50 dark:bg-red-900/10 border-2 border-red-200 dark:border-red-800 rounded-xl p-6">
              <div className="flex items-center gap-3 mb-4">
                <IconContainer icon={AlertTriangle} color="red" />
                <div>
                  <h2 className="text-xl font-semibold text-red-900 dark:text-red-100">Danger Zone</h2>
                  <p className="text-sm text-red-600 dark:text-red-300">Irreversible actions</p>
                </div>
              </div>

              <h3 className="text-lg font-semibold text-red-900 dark:text-red-100 mb-2">Delete Account</h3>
              <p className="text-red-700 dark:text-red-300 mb-4">
                Once you delete your account, there is no going back. This action will permanently delete your account
                and all associated data in accordance with GDPR and CCPA regulations.
              </p>
              <Button
                variant="primary"
                onClick={() => setShowDeleteModal(true)}
                className="bg-red-600 hover:bg-red-700"
              >
                <Trash2 className="h-4 w-4" />
                Delete Account
              </Button>
            </div>

            {/* Save Button */}
            <Card>
              <CardContent>
                <Button
                  onClick={handleSaveAll}
                  disabled={isSaving}
                  className="w-full"
                >
                  {isSaving ? <Loader2 className="h-5 w-5 animate-spin" /> : <Save className="h-5 w-5" />}
                  Save All Changes
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      {/* Delete Account Modal */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => {
          setShowDeleteModal(false);
          setDeleteConfirmText("");
        }}
        title={
          <div className="flex items-center gap-3">
            <IconContainer icon={AlertTriangle} color="red" />
            <span>Delete Account</span>
          </div>
        }
        size="md"
      >
        <p className="text-slate-600 dark:text-md-on-surface-variant mb-4">
          This action cannot be undone. This will permanently delete your account and remove your data from our
          servers.
        </p>

        <div className="bg-slate-100 dark:bg-md-surface-container-high rounded-lg p-4 mb-4">
          <p className="text-sm text-slate-700 dark:text-md-on-surface-variant mb-2">
            Please type <strong className="text-red-600">DELETE</strong> to confirm:
          </p>
          <Input
            type="text"
            value={deleteConfirmText}
            onChange={(e) => setDeleteConfirmText(e.target.value)}
            placeholder="Type DELETE"
          />
        </div>

        <div className="flex gap-3">
          <Button
            variant="secondary"
            onClick={() => {
              setShowDeleteModal(false);
              setDeleteConfirmText("");
            }}
            className="flex-1"
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleDeleteAccount}
            disabled={isSaving || deleteConfirmText !== "DELETE"}
            className="flex-1 bg-red-600 hover:bg-red-700"
          >
            {isSaving ? <Loader2 className="h-4 w-4 animate-spin mx-auto" /> : "Delete Account"}
          </Button>
        </div>
      </Modal>
    </div>
  )
}
