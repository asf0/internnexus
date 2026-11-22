import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ActiveFilterSummary } from '@/components/toolbar/ActiveFilterSummary';

afterEach(() => {
  cleanup();
});

describe('ActiveFilterSummary', () => {
  it('shows active filters and removes the selected item', async () => {
    const onRemove = vi.fn();
    const user = userEvent.setup();
    render(<ActiveFilterSummary items={[{ id: 'remote', label: 'Remote', onRemove }]} />);

    await user.click(screen.getByRole('button', { name: 'Remove Remote filter' }));
    expect(onRemove).toHaveBeenCalledOnce();
  });

  it('renders nothing without active filters', () => {
    render(<ActiveFilterSummary items={[]} />);

    expect(screen.queryByRole('group', { name: 'Active job filters' })).not.toBeInTheDocument();
  });
});
