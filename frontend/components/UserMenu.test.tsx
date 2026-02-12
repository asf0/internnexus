/// <reference lib="dom" />

import { describe, test, expect, mock, beforeEach } from 'bun:test';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import React from 'react';

// Mock next-auth/react
const mockSignOut = mock();
const mockUseSession = mock();

mock.module('next-auth/react', () => ({
  signOut: mock(() => mockSignOut()),
  useSession: mock(() => mockUseSession()),
}));

// Mock next/link
mock.module('next/link', () => {
  return ({ children, href, onClick }: { children: React.ReactNode; href: string; onClick?: () => void }) => (
    React.createElement('a', { href, onClick }, children)
  );
});

// Dynamic import for the component after mocks
let UserMenu: typeof import('./UserMenu').default;

describe('UserMenu Component', () => {
  beforeEach(async () => {
    mockSignOut.mockClear();
    mockUseSession.mockClear();
    const module = await import('./UserMenu');
    UserMenu = module.default;
  });

  describe('Loading State', () => {
    test('renders loading skeleton when session is loading', () => {
      mockUseSession.mockReturnValue({ data: null, status: 'loading' });
      
      render(React.createElement(UserMenu));
      
      const skeleton = document.querySelector('.animate-pulse');
      expect(skeleton).toBeInTheDocument();
    });
  });

  describe('Unauthenticated State', () => {
    beforeEach(() => {
      mockUseSession.mockReturnValue({ data: null, status: 'unauthenticated' });
    });

    test('renders sign in button when not authenticated', () => {
      render(React.createElement(UserMenu));
      
      expect(screen.getByText('Sign in')).toBeInTheDocument();
    });

    test('opens auth modal when sign in button is clicked', () => {
      render(React.createElement(UserMenu));
      
      const signInButton = screen.getByText('Sign in');
      fireEvent.click(signInButton);
      
      // AuthModal should be rendered (checking for its content)
      expect(screen.getByText('Welcome to InternNexus')).toBeInTheDocument();
    });

    test('opens auth modal in register mode when toggled', () => {
      render(React.createElement(UserMenu));
      
      const signInButton = screen.getByText('Sign in');
      fireEvent.click(signInButton);
      
      // Modal should open in login mode by default
      expect(screen.getByText('Continue with GitHub')).toBeInTheDocument();
    });
  });

  describe('Authenticated State', () => {
    const mockSession = {
      user: {
        name: 'John Doe',
        email: 'john@example.com',
        image: 'https://example.com/avatar.jpg',
      },
    };

    beforeEach(() => {
      mockUseSession.mockReturnValue({ data: mockSession, status: 'authenticated' });
    });

    test('renders user avatar when authenticated', () => {
      render(React.createElement(UserMenu));
      
      const avatar = screen.getByAltText('John Doe');
      expect(avatar).toBeInTheDocument();
      expect(avatar).toHaveAttribute('src', 'https://example.com/avatar.jpg');
    });

    test('renders user name when authenticated', () => {
      render(React.createElement(UserMenu));
      
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    test('renders default avatar when no image is provided', () => {
      mockUseSession.mockReturnValue({
        data: { user: { name: 'Jane Doe', email: 'jane@example.com' } },
        status: 'authenticated',
      });
      
      render(React.createElement(UserMenu));
      
      const defaultAvatar = document.querySelector('.bg-blue-600');
      expect(defaultAvatar).toBeInTheDocument();
    });

    test('renders email when name is not available', () => {
      mockUseSession.mockReturnValue({
        data: { user: { email: 'jane@example.com' } },
        status: 'authenticated',
      });
      
      render(React.createElement(UserMenu));
      
      expect(screen.getByText('jane@example.com')).toBeInTheDocument();
    });

    test('opens dropdown menu when user button is clicked', () => {
      render(React.createElement(UserMenu));
      
      const userButton = screen.getByText('John Doe').closest('button');
      fireEvent.click(userButton!);
      
      expect(screen.getByText('My Profile')).toBeInTheDocument();
      expect(screen.getByText('Account Settings')).toBeInTheDocument();
      expect(screen.getByText('Sign out')).toBeInTheDocument();
    });

    test('closes dropdown when clicking outside', () => {
      render(React.createElement(UserMenu));
      
      const userButton = screen.getByText('John Doe').closest('button');
      fireEvent.click(userButton!);
      
      expect(screen.getByText('My Profile')).toBeInTheDocument();
      
      // Click outside overlay
      const overlay = document.querySelector('.fixed.inset-0');
      fireEvent.click(overlay!);
      
      expect(screen.queryByText('My Profile')).not.toBeInTheDocument();
    });

    test('navigates to profile page when My Profile is clicked', () => {
      render(React.createElement(UserMenu));
      
      const userButton = screen.getByText('John Doe').closest('button');
      fireEvent.click(userButton!);
      
      const profileLink = screen.getByText('My Profile').closest('a');
      expect(profileLink).toHaveAttribute('href', '/profile');
    });

    test('navigates to settings page when Account Settings is clicked', () => {
      render(React.createElement(UserMenu));
      
      const userButton = screen.getByText('John Doe').closest('button');
      fireEvent.click(userButton!);
      
      const settingsLink = screen.getByText('Account Settings').closest('a');
      expect(settingsLink).toHaveAttribute('href', '/settings');
    });

    test('calls signOut when Sign out is clicked', async () => {
      mockSignOut.mockResolvedValue(undefined);
      
      render(React.createElement(UserMenu));
      
      const userButton = screen.getByText('John Doe').closest('button');
      fireEvent.click(userButton!);
      
      const signOutButton = screen.getByText('Sign out');
      fireEvent.click(signOutButton);
      
      await waitFor(() => {
        expect(mockSignOut).toHaveBeenCalledWith({ callbackUrl: '/' });
      });
    });

    test('displays user email in dropdown', () => {
      render(React.createElement(UserMenu));
      
      const userButton = screen.getByText('John Doe').closest('button');
      fireEvent.click(userButton!);
      
      expect(screen.getByText('john@example.com')).toBeInTheDocument();
    });

    test('truncates long email addresses', () => {
      mockUseSession.mockReturnValue({
        data: {
          user: {
            name: 'John Doe',
            email: 'very.long.email.address@example.com',
          },
        },
        status: 'authenticated',
      });
      
      render(React.createElement(UserMenu));
      
      const userButton = screen.getByText('John Doe').closest('button');
      fireEvent.click(userButton!);
      
      const emailElement = screen.getByText('very.long.email.address@example.com');
      expect(emailElement).toHaveClass('truncate');
    });
  });

  describe('Accessibility', () => {
    test('has proper button roles', () => {
      mockUseSession.mockReturnValue({ data: null, status: 'unauthenticated' });
      
      render(React.createElement(UserMenu));
      
      const signInButton = screen.getByRole('button', { name: /sign in/i });
      expect(signInButton).toBeInTheDocument();
    });

    test('dropdown menu is keyboard accessible', () => {
      const mockSession = {
        user: { name: 'John Doe', email: 'john@example.com' },
      };
      mockUseSession.mockReturnValue({ data: mockSession, status: 'authenticated' });
      
      render(React.createElement(UserMenu));
      
      const userButton = screen.getByText('John Doe').closest('button');
      fireEvent.click(userButton!);
      
      expect(screen.getByText('My Profile')).toBeInTheDocument();
    });
  });
});
