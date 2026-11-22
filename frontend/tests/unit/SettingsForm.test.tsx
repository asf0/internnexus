import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { UserProfile } from '@/lib/types/user';

const mocks = vi.hoisted(() => ({
  back: vi.fn(),
  refresh: vi.fn(),
  push: vi.fn(),
  updateSession: vi.fn(),
  updateUserProfile: vi.fn(),
  changePassword: vi.fn(),
  deleteAccount: vi.fn(),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ back: mocks.back, refresh: mocks.refresh, push: mocks.push }),
}));

vi.mock('next-auth/react', () => ({
  useSession: () => ({ update: mocks.updateSession }),
}));

vi.mock('@/app/actions/user', () => ({
  updateUserProfile: mocks.updateUserProfile,
  changePassword: mocks.changePassword,
  deleteAccount: mocks.deleteAccount,
}));

import SettingsForm from '@/components/settings/SettingsForm';

const profile: UserProfile = {
  id: 'user-1',
  email: 'person@example.com',
  name: 'Existing Name',
  image: null,
  created_at: '2026-01-01T00:00:00Z',
  bio: null,
  phone: null,
  location: null,
  job_title: null,
  company: null,
  industry: null,
  skills: [],
  linkedin_url: null,
  portfolio_url: null,
  preferred_locations: [],
  has_password: true,
};

describe('SettingsForm', () => {
  beforeEach(() => {
    Object.values(mocks).forEach((mock) => mock.mockReset());
    mocks.updateUserProfile.mockResolvedValue({
      success: true,
      name: 'Updated Name',
      image: null,
    });
    mocks.updateSession.mockResolvedValue(undefined);
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('enables saving only after a change and returns to a saved state', async () => {
    const user = userEvent.setup();
    render(<SettingsForm profile={profile} />);

    const saveButton = screen.getByRole('button', { name: /save all changes/i });
    expect(saveButton).toBeDisabled();
    expect(screen.getByText('All changes are saved.')).toBeInTheDocument();

    const nameInput = screen.getByLabelText('Full Name');
    await user.clear(nameInput);
    await user.type(nameInput, 'Updated Name');

    expect(saveButton).toBeEnabled();
    expect(screen.getByText('You have unsaved changes.')).toBeInTheDocument();

    await user.click(saveButton);

    await waitFor(() => expect(mocks.updateUserProfile).toHaveBeenCalledOnce());
    expect(mocks.updateUserProfile).toHaveBeenCalledWith(
      expect.objectContaining({ name: 'Updated Name' })
    );
    await waitFor(() => expect(saveButton).toBeDisabled());
    expect(screen.getByText('All changes are saved.')).toBeInTheDocument();
  });
});
