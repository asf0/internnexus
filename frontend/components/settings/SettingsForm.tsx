'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from 'next-auth/react';
import { ArrowLeft, Save, Loader2 } from 'lucide-react';
import { updateUserProfile, changePassword, deleteAccount } from '@/app/actions/user';
import { calculateStrength } from '@/components/common';
import { Button, Alert, PageHeader } from '@/components/ui';
import {
  AgentAccessSection,
  PersonalSection,
  ProfessionalSection,
  PasswordSection,
  DangerZone,
} from './index';
import type { MCPApiKey, UserProfile } from '@/lib/types/user';
import { userProfileSchema } from '@/lib/validation';

const normalizeOptional = (value: string | null | undefined): string | null =>
  value?.trim() || null;

function getPasswordError(
  passwordForm: { current_password: string; new_password: string; confirm_password: string },
  hasExistingPassword: boolean
): string | null {
  if (!passwordForm.new_password || !passwordForm.confirm_password) {
    return 'Enter and confirm your new password';
  }
  if (hasExistingPassword && !passwordForm.current_password) {
    return 'Enter your current password';
  }
  if (passwordForm.new_password !== passwordForm.confirm_password) {
    return 'New passwords do not match';
  }
  if (calculateStrength(passwordForm.new_password).score < 100) {
    return 'Password does not meet all requirements';
  }
  if (passwordForm.new_password === passwordForm.current_password) {
    return 'New password cannot be the same as current password';
  }
  return null;
}

interface SettingsFormProps {
  readonly profile: UserProfile;
  readonly mcpKeys?: MCPApiKey[];
  readonly mcpEndpoint?: string;
}

export default function SettingsForm({
  profile,
  mcpKeys = [],
  mcpEndpoint = 'http://localhost:8001/mcp',
}: SettingsFormProps) {
  const router = useRouter();
  const { update: updateSession } = useSession();
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const [personalForm, setPersonalForm] = useState({
    name: profile.name || '',
    bio: profile.bio || '',
    phone: profile.phone || '',
    location: profile.location || '',
  });

  const [professionalForm, setProfessionalForm] = useState({
    job_title: profile.job_title || '',
    company: profile.company || '',
    industry: profile.industry || '',
    linkedin_url: profile.linkedin_url || '',
    portfolio_url: profile.portfolio_url || '',
  });

  const [skills, setSkills] = useState<string[]>(profile.skills || []);
  const [preferredLocations, setPreferredLocations] = useState<string[]>(
    profile.preferred_locations || []
  );

  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  });

  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');
  const profilePayload = useMemo(
    () => ({
      name: normalizeOptional(personalForm.name),
      bio: normalizeOptional(personalForm.bio),
      phone: normalizeOptional(personalForm.phone),
      location: normalizeOptional(personalForm.location),
      job_title: normalizeOptional(professionalForm.job_title),
      company: normalizeOptional(professionalForm.company),
      industry: normalizeOptional(professionalForm.industry),
      linkedin_url: normalizeOptional(professionalForm.linkedin_url),
      portfolio_url: normalizeOptional(professionalForm.portfolio_url),
      skills,
      preferred_locations: preferredLocations,
    }),
    [personalForm, professionalForm, skills, preferredLocations]
  );
  const [savedProfileSnapshot, setSavedProfileSnapshot] = useState(() =>
    JSON.stringify({
      name: profile.name || null,
      bio: profile.bio || null,
      phone: profile.phone || null,
      location: profile.location || null,
      job_title: profile.job_title || null,
      company: profile.company || null,
      industry: profile.industry || null,
      linkedin_url: profile.linkedin_url || null,
      portfolio_url: profile.portfolio_url || null,
      skills: profile.skills || [],
      preferred_locations: profile.preferred_locations || [],
    })
  );
  const hasPasswordChanges = Object.values(passwordForm).some(Boolean);
  const isDirty = JSON.stringify(profilePayload) !== savedProfileSnapshot || hasPasswordChanges;

  useEffect(() => {
    if (!isDirty) return;

    const warnAboutUnsavedChanges = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };
    window.addEventListener('beforeunload', warnAboutUnsavedChanges);
    return () => window.removeEventListener('beforeunload', warnAboutUnsavedChanges);
  }, [isDirty]);

  const handleSaveAll = async () => {
    setIsSaving(true);
    setMessage(null);

    const profileValidation = userProfileSchema.safeParse(profilePayload);
    if (!profileValidation.success) {
      setMessage({
        type: 'error',
        text: profileValidation.error.issues[0]?.message || 'Invalid profile data',
      });
      setIsSaving(false);
      return;
    }

    if (hasPasswordChanges) {
      const passwordError = getPasswordError(passwordForm, profile.has_password);
      if (passwordError) {
        setMessage({ type: 'error', text: passwordError });
        setIsSaving(false);
        return;
      }
    }

    const profileResult = await updateUserProfile(profileValidation.data);

    if (!profileResult.success) {
      setMessage({ type: 'error', text: profileResult.error || 'Failed to save profile changes' });
      setIsSaving(false);
      return;
    }

    setSavedProfileSnapshot(JSON.stringify(profilePayload));

    // Keep the toolbar identity current.
    try {
      await updateSession({ name: profileResult.name, image: profileResult.image });
    } catch (err) {
      console.error('Failed to refresh session after profile update', err);
    }

    if (hasPasswordChanges) {
      const passwordResult = await changePassword({
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password,
      });

      if (!passwordResult.success) {
        setMessage({ type: 'error', text: passwordResult.error || 'Failed to change password' });
        setIsSaving(false);
        return;
      }

      setPasswordForm({ current_password: '', new_password: '', confirm_password: '' });
      setIsSaving(false);
      router.push('/?auth=required');
      router.refresh();
      return;
    }

    setMessage({ type: 'success', text: 'All changes saved successfully!' });
    router.refresh();
    setIsSaving(false);
  };

  const handleDeleteAccount = async () => {
    setIsDeleting(true);
    const result = await deleteAccount();

    if (result.success) {
      setIsDeleting(false);
      router.push('/');
    } else {
      setMessage({ type: 'error', text: result.error || 'Failed to delete account' });
      setIsDeleting(false);
    }
  };

  const handlePersonalChange = (field: string, value: string) => {
    setPersonalForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleProfessionalChange = (field: string, value: string) => {
    setProfessionalForm((prev) => ({ ...prev, [field]: value }));
  };

  const addSkill = (skill: string) => {
    const trimmed = skill.trim();
    if (trimmed && !skills.includes(trimmed)) {
      setSkills((prev) => [...prev, trimmed]);
    }
  };

  const removeSkill = (skill: string) => {
    setSkills((prev) => prev.filter((s) => s !== skill));
  };

  const addLocation = (location: string) => {
    const trimmed = location.trim();
    if (trimmed && !preferredLocations.includes(trimmed)) {
      setPreferredLocations((prev) => [...prev, trimmed]);
    }
  };

  const removeLocation = (location: string) => {
    setPreferredLocations((prev) => prev.filter((l) => l !== location));
  };

  return (
    <div className="py-2 sm:py-4">
      <div className="mx-auto max-w-6xl">
        <Button
          variant="ghost"
          onClick={() => {
            if (!isDirty || window.confirm('Discard your unsaved changes and leave this page?')) {
              router.back();
            }
          }}
          className="mb-6"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </Button>

        <PageHeader
          title="Account Settings"
          description="Manage your profile, security, and integrations."
          className="mb-8"
        />

        {message && (
          <Alert type={message.type} className="mb-6">
            {message.text}
          </Alert>
        )}

        <div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-12">
          <div className="space-y-6 xl:col-span-4">
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
              onCurrentPasswordChange={(value) =>
                setPasswordForm((prev) => ({ ...prev, current_password: value }))
              }
              onNewPasswordChange={(value) =>
                setPasswordForm((prev) => ({ ...prev, new_password: value }))
              }
              onConfirmPasswordChange={(value) =>
                setPasswordForm((prev) => ({ ...prev, confirm_password: value }))
              }
            />
          </div>

          <div className="min-w-0 space-y-6 xl:col-span-8">
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

            <AgentAccessSection initialKeys={mcpKeys} mcpEndpoint={mcpEndpoint} />

            <DangerZone
              showDeleteModal={showDeleteModal}
              deleteConfirmText={deleteConfirmText}
              isDeleting={isDeleting}
              onDeleteModalOpen={() => setShowDeleteModal(true)}
              onDeleteModalClose={() => {
                setShowDeleteModal(false);
                setDeleteConfirmText('');
              }}
              onDeleteConfirmTextChange={setDeleteConfirmText}
              onDeleteAccount={handleDeleteAccount}
            />

            <div className="border-border bg-surface/95 sticky bottom-4 z-20 flex flex-col gap-3 rounded-xl border p-4 shadow-lg backdrop-blur sm:flex-row sm:items-center sm:justify-between">
              <p className="text-foreground-secondary text-sm" aria-live="polite">
                {isDirty ? 'You have unsaved changes.' : 'All changes are saved.'}
              </p>
              <Button
                onClick={handleSaveAll}
                disabled={isSaving || !isDirty}
                className="w-full sm:w-auto"
              >
                {isSaving ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Save className="h-5 w-5" />
                )}
                Save All Changes
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
