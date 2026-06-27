import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import LocationSelect from '@/components/common/LocationSelect';
import { MatchFacetsResponseSchema } from '@/lib/schemas';
import type { LocationItem } from '@/lib/types';

const locations: LocationItem[] = [
  {
    value: 'Brazil',
    label: 'Brazil',
    count: 12,
    type: 'country',
    country: 'Brazil',
    children: [
      {
        value: 'Sao Paulo',
        label: 'Sao Paulo',
        count: 7,
        type: 'state',
        country: 'Brazil',
        state: 'Sao Paulo',
        children: null,
      },
    ],
  },
];

afterEach(() => {
  cleanup();
});

describe('LocationSelect', () => {
  it('accepts matched facet leaves with null children', () => {
    const result = MatchFacetsResponseSchema.parse({
      companies: [],
      categories: [],
      job_types: [],
      work_modes: [],
      locations,
      total_matches: 12,
    });

    expect(result.locations.at(0)?.children?.at(0)?.children).toBeNull();
  });

  it('selects a parent country when its name is clicked', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <LocationSelect
        locations={locations}
        selected={[]}
        onChange={onChange}
        placeholder="Location"
      />
    );

    await user.click(screen.getByRole('button', { name: 'Location' }));
    await user.click(screen.getByRole('option', { name: /Brazil/ }));

    expect(onChange).toHaveBeenCalledWith(['Brazil']);
  });

  it('uses a separate control to browse child locations and refreshes counts', async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      <LocationSelect
        locations={locations}
        selected={[]}
        onChange={vi.fn()}
        placeholder="Location"
      />
    );

    await user.click(screen.getByRole('button', { name: 'Location' }));
    expect(screen.getByText('(12)')).toBeInTheDocument();

    rerender(
      <LocationSelect
        locations={[{ ...locations[0], count: 4 }]}
        selected={[]}
        onChange={vi.fn()}
        placeholder="Location"
      />
    );
    expect(screen.getByText('(4)')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Browse Brazil' }));
    expect(screen.getByRole('option', { name: /Sao Paulo/ })).toBeInTheDocument();
  });
});
