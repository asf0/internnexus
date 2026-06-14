import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/react';
import { AdminTabs } from '@/components/admin/ui/AdminTabs';

afterEach(() => {
  cleanup();
});

describe('AdminTabs', () => {
  it('renders tab labels and shows the first panel by default', () => {
    render(
      <AdminTabs
        items={[
          { key: 'one', label: 'First', children: <div>First panel</div> },
          { key: 'two', label: 'Second', children: <div>Second panel</div> },
        ]}
      />
    );

    expect(screen.getByRole('tab', { name: 'First' })).toBeDefined();
    expect(screen.getByRole('tab', { name: 'Second' })).toBeDefined();
    expect(screen.getByText('First panel')).toBeDefined();
    expect(screen.queryByText('Second panel')).toBeNull();
  });

  it('switches panels when a tab is clicked', () => {
    const onChange = vi.fn();
    render(
      <AdminTabs
        items={[
          { key: 'one', label: 'First', children: <div>First panel</div> },
          { key: 'two', label: 'Second', children: <div>Second panel</div> },
        ]}
        onChange={onChange}
      />
    );

    fireEvent.click(screen.getByRole('tab', { name: 'Second' }));

    expect(screen.getByText('Second panel')).toBeDefined();
    expect(screen.queryByText('First panel')).toBeNull();
    expect(onChange).toHaveBeenCalledWith('two');
  });

  it('respects controlled activeKey', () => {
    render(
      <AdminTabs
        activeKey="two"
        items={[
          { key: 'one', label: 'First', children: <div>First panel</div> },
          { key: 'two', label: 'Second', children: <div>Second panel</div> },
        ]}
      />
    );

    expect(screen.getByText('Second panel')).toBeDefined();
    expect(screen.queryByText('First panel')).toBeNull();
  });
});
