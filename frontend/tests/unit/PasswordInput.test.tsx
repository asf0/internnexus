import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PasswordInput from '@/components/common/PasswordInput';

afterEach(() => {
  cleanup();
});

describe('PasswordInput', () => {
  it('toggles password visibility and updates aria-label', async () => {
    const user = userEvent.setup();
    render(<PasswordInput value="secret" onChange={vi.fn()} id="password" />);

    const input = screen.getByLabelText('Password');
    expect(input).toHaveAttribute('type', 'password');

    const toggle = screen.getByRole('button', { name: /show password/i });
    expect(toggle).not.toHaveAttribute('tabIndex');

    await user.click(toggle);
    expect(input).toHaveAttribute('type', 'text');
    expect(screen.getByRole('button', { name: /hide password/i })).toBeDefined();
  });

  it('keeps confirm password toggle reachable and labelled', async () => {
    const user = userEvent.setup();
    render(
      <PasswordInput
        value="secret"
        onChange={vi.fn()}
        confirmValue="secret"
        onConfirmChange={vi.fn()}
        showConfirmation
      />
    );

    const toggle = screen.getByRole('button', { name: /show confirm password/i });
    expect(toggle).toBeDefined();

    await user.click(toggle);
    expect(screen.getByRole('button', { name: /hide confirm password/i })).toBeDefined();
  });
});
