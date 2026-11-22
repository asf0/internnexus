import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SearchInput } from '@/components/toolbar/SearchInput';

afterEach(() => {
  cleanup();
});

const defaultProps = {
  value: '',
  onChange: vi.fn(),
  onSubmit: vi.fn(),
  onClear: vi.fn(),
  showFilters: false,
};

describe('SearchInput', () => {
  it('opens search guidance on click and closes it with Escape', async () => {
    const user = userEvent.setup();
    render(<SearchInput {...defaultProps} />);

    await user.click(screen.getByRole('button', { name: 'Search tips' }));
    expect(screen.getByRole('note')).toHaveTextContent('Search syntax');

    await user.keyboard('{Escape}');
    expect(screen.queryByRole('note')).not.toBeInTheDocument();
  });

  it('closes search guidance when the filter panel opens', async () => {
    const user = userEvent.setup();
    const { rerender } = render(<SearchInput {...defaultProps} />);

    await user.click(screen.getByRole('button', { name: 'Search tips' }));
    rerender(<SearchInput {...defaultProps} showFilters />);

    expect(screen.queryByRole('note')).not.toBeInTheDocument();
  });
});
