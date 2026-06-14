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
    expect(trigger).toHaveAttribute('aria-haspopup', 'listbox');
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
  });

  it('opens the listbox and exposes options with aria-selected', async () => {
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

    const listbox = screen.getByRole('listbox');
    expect(listbox).toHaveAttribute('aria-multiselectable', 'true');

    const optionElements = screen.getAllByRole('option');
    expect(optionElements).toHaveLength(3);
    expect(optionElements[0]).toHaveAttribute('aria-selected', 'true');
    expect(optionElements[1]).toHaveAttribute('aria-selected', 'false');
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
    await user.click(screen.getByRole('option', { name: 'Hybrid' }));

    expect(handleChange).toHaveBeenCalledWith(['hybrid']);
  });
});
