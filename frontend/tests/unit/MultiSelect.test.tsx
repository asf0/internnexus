import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MultiSelect from '@/components/common/MultiSelect';

afterEach(() => {
  cleanup();
});

const options = ['remote', 'hybrid', 'onsite'];
const labelMap = { remote: 'Remote', hybrid: 'Hybrid', onsite: 'On-site' };

describe('MultiSelect', () => {
  it('renders the trigger button with listbox semantics', () => {
    render(
      <MultiSelect
        options={options}
        selected={[]}
        onChange={vi.fn()}
        placeholder="Select locations"
        labelMap={labelMap}
      />
    );

    const trigger = screen.getByRole('button', { name: /select locations/i });
    expect(trigger).toHaveAttribute('aria-haspopup', 'menu');
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
  });

  it('opens the menu and exposes checked options', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(
      <MultiSelect
        options={options}
        selected={['remote']}
        onChange={handleChange}
        placeholder="Select locations"
        labelMap={labelMap}
      />
    );

    await user.click(screen.getByRole('button', { name: /select locations/i }));

    expect(screen.getByRole('menu')).toBeInTheDocument();

    const optionElements = screen.getAllByRole('menuitemcheckbox');
    expect(optionElements).toHaveLength(3);
    expect(optionElements[0]).toHaveAttribute('aria-checked', 'true');
    expect(optionElements[1]).toHaveAttribute('aria-checked', 'false');
  });

  it('toggles options with click', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(
      <MultiSelect
        options={options}
        selected={[]}
        onChange={handleChange}
        placeholder="Select locations"
        labelMap={labelMap}
      />
    );

    await user.click(screen.getByRole('button', { name: /select locations/i }));
    await user.click(screen.getByRole('menuitemcheckbox', { name: 'Hybrid' }));

    expect(handleChange).toHaveBeenCalledWith(['hybrid']);
  });

  it('focuses search when opened and closes with Escape', async () => {
    const user = userEvent.setup();
    render(
      <MultiSelect
        options={options}
        selected={[]}
        onChange={vi.fn()}
        placeholder="Select locations"
        labelMap={labelMap}
      />
    );

    const trigger = screen.getByRole('button', { name: /select locations/i });
    await user.click(trigger);
    expect(screen.getByPlaceholderText('Search...')).toHaveFocus();

    await user.keyboard('{Escape}');
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
  });
});
