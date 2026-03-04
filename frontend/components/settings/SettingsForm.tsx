"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useSession } from "next-auth/react"
import { ArrowLeft, Save, Loader2 } from "lucide-react"
import { updateUserProfile, changePassword, deleteAccount } from "@/app/actions/user"
import { calculateStrength } from "@/components/common"
import { Button, Card, CardContent, Alert } from "@/components/ui"
import { PersonalSection, ProfessionalSection, PasswordSection, DangerZone } from "./index"
import type { UserProfile } from "@/lib/types/user"

interface SettingsFormProps {
  readonly profile: UserProfile;
}

export default function SettingsForm({ profile }: SettingsFormProps) {
  const router = useRouter()
  const { update: updateSession } = useSession()
  const [isSaving, setIsSaving] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null)

  const [personalForm, setPersonalForm] = useState({
    name: profile.name || "",
    bio: profile.bio || "",
    phone: profile.phone || "",
    location: profile.location || "",
  })

  const [professionalForm, setProfessionalForm] = useState({
    job_title: profile.job_title || "",
    company: profile.company || "",
    industry: profile.industry || "",
    linkedin_url: profile.linkedin_url || "",
    portfolio_url: profile.portfolio_url || "",
  })

  const [skills, setSkills] = useState<string[]>(profile.skills || [])
  const [preferredLocations, setPreferredLocations] = useState<string[]>(profile.preferred_locations || [])

  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  })

  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [deleteConfirmText, setDeleteConfirmText] = useState("")

  const handleSaveAll = async () => {
    setIsSaving(true)
    setMessage(null)

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

      if (passwordForm.new_password === passwordForm.current_password) {
        setMessage({ type: "error", text: "New password cannot be the same as current password" })
        setIsSaving(false)
        return
      }
    }

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

    // Patch the NextAuth JWT so the toolbar name/image updates immediately
    await updateSession({ name: profileResult.name, image: profileResult.image })

    if (passwordForm.current_password) {
      const passwordResult = await changePassword({
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password,
      })

      if (!passwordResult.success) {
        setMessage({ type: "error", text: passwordResult.error || "Failed to change password" })
        setIsSaving(false)
        return
      }

      setPasswordForm({ current_password: "", new_password: "", confirm_password: "" })
    }

    setMessage({ type: "success", text: "All changes saved successfully!" })
    router.refresh()
    setIsSaving(false)
  }

  const handleDeleteAccount = async () => {
    setIsDeleting(true)
    const result = await deleteAccount()

    if (result.success) {
      setIsDeleting(false)
      router.push("/")
    } else {
      setMessage({ type: "error", text: result.error || "Failed to delete account" })
      setIsDeleting(false)
    }
  }

  const handlePersonalChange = (field: string, value: string) => {
    setPersonalForm(prev => ({ ...prev, [field]: value }))
  }

  const handleProfessionalChange = (field: string, value: string) => {
    setProfessionalForm(prev => ({ ...prev, [field]: value }))
  }

  const addSkill = (skill: string) => {
    const trimmed = skill.trim()
    if (trimmed && !skills.includes(trimmed)) {
      setSkills(prev => [...prev, trimmed])
    }
  }

  const removeSkill = (skill: string) => {
    setSkills(prev => prev.filter(s => s !== skill))
  }

  const addLocation = (location: string) => {
    const trimmed = location.trim()
    if (trimmed && !preferredLocations.includes(trimmed)) {
      setPreferredLocations(prev => [...prev, trimmed])
    }
  }

  const removeLocation = (location: string) => {
    setPreferredLocations(prev => prev.filter(l => l !== location))
  }

  return (
    <div className="py-8 px-4">
      <div className="max-w-7xl mx-auto">
        <Button
          variant="ghost"
          onClick={() => router.back()}
          className="mb-6"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </Button>

        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 dark:text-md-on-surface">Account Settings</h1>
          <p className="mt-1 text-slate-600 dark:text-md-on-surface-variant">Manage your profile and account preferences</p>
        </div>

        {message && (
          <Alert type={message.type} className="mb-6">
            {message.text}
          </Alert>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 space-y-6">
            <PersonalSection
              name={personalForm.name}
              bio={personalForm.bio}
              phone={personalForm.phone}
              location={personalForm.location}
              onChange={handlePersonalChange}
            />

            <PasswordSection
              hasPassword={profile.has_password}
              currentPassword={passwordForm.current_password}
              newPassword={passwordForm.new_password}
              confirmPassword={passwordForm.confirm_password}
              onCurrentPasswordChange={(value) => setPasswordForm(prev => ({ ...prev, current_password: value }))}
              onNewPasswordChange={(value) => setPasswordForm(prev => ({ ...prev, new_password: value }))}
              onConfirmPasswordChange={(value) => setPasswordForm(prev => ({ ...prev, confirm_password: value }))}
            />
          </div>

          <div className="lg:col-span-2 space-y-6">
            <ProfessionalSection
              jobTitle={professionalForm.job_title}
              company={professionalForm.company}
              industry={professionalForm.industry}
              linkedinUrl={professionalForm.linkedin_url}
              portfolioUrl={professionalForm.portfolio_url}
              skills={skills}
              preferredLocations={preferredLocations}
              onFieldChange={handleProfessionalChange}
              onAddSkill={addSkill}
              onRemoveSkill={removeSkill}
              onAddLocation={addLocation}
              onRemoveLocation={removeLocation}
            />

            <DangerZone
              showDeleteModal={showDeleteModal}
              deleteConfirmText={deleteConfirmText}
              isDeleting={isDeleting}
              onDeleteModalOpen={() => setShowDeleteModal(true)}
              onDeleteModalClose={() => {
                setShowDeleteModal(false)
                setDeleteConfirmText("")
              }}
              onDeleteConfirmTextChange={setDeleteConfirmText}
              onDeleteAccount={handleDeleteAccount}
            />

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
    </div>
  )
}
