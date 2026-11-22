import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Footer from '@/components/common/Footer';
import AboutModal from '@/components/modals/AboutModal';
import PrivacyModal from '@/components/modals/PrivacyModal';
import TermsModal from '@/components/modals/TermsModal';

afterEach(() => {
  cleanup();
});

describe('informational modals', () => {
  it.each([
    ['About', 'About InternNexus'],
    ['Privacy', 'Privacy Policy'],
    ['Terms', 'Terms of Service'],
  ])('opens %s from the footer', async (triggerName, dialogName) => {
    const user = userEvent.setup();
    render(<Footer />);

    const link = screen.getByRole('link', { name: triggerName });
    expect(link).toHaveAttribute('href', `/${triggerName.toLowerCase()}`);
    await user.click(link);

    expect(screen.getByRole('dialog', { name: dialogName })).toBeInTheDocument();
  });

  it('describes the current product without stale inventory counts', () => {
    render(<AboutModal isOpen onClose={vi.fn()} />);

    expect(screen.getByRole('heading', { name: 'About InternNexus' })).toBeInTheDocument();
    expect(screen.getByText('Unified search')).toBeInTheDocument();
    expect(screen.getByText('Resume matching')).toBeInTheDocument();
    expect(screen.queryByText(/15k\\+/i)).not.toBeInTheDocument();
  });

  it('documents the data used by current account and matching features', () => {
    render(<PrivacyModal isOpen onClose={vi.fn()} />);

    expect(screen.getByRole('heading', { name: 'Privacy Policy' })).toBeInTheDocument();
    expect(screen.getByText('Information we collect')).toBeInTheDocument();
    expect(screen.getByText('Cookies and local storage')).toBeInTheDocument();
    expect(screen.getByText(/shortened hash derived from your IP address/i)).toBeInTheDocument();
    expect(screen.getByText(/July 3, 2026/i)).toBeInTheDocument();
  });

  it('explains third-party listings and automated matching limitations', () => {
    render(<TermsModal isOpen onClose={vi.fn()} />);

    expect(screen.getByRole('heading', { name: 'Terms of Service' })).toBeInTheDocument();
    expect(screen.getByText('Job listings and matching')).toBeInTheDocument();
    expect(screen.getByText(/automated estimates for discovery only/i)).toBeInTheDocument();
  });

  it('closes on Escape', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<PrivacyModal isOpen onClose={onClose} />);

    await user.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalledOnce();
  });
});
