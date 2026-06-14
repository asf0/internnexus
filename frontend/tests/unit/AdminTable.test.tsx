import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/react';
import { AdminTable } from '@/components/admin/ui/AdminTable';

interface Item {
  readonly id: string;
  readonly name: string;
  readonly count: number;
}

const data: Item[] = [
  { id: 'a', name: 'Alpha', count: 1 },
  { id: 'b', name: 'Beta', count: 2 },
];

const columns = [
  { title: 'Name', dataIndex: 'name', key: 'name' },
  { title: 'Count', dataIndex: 'count', key: 'count' },
];

afterEach(() => {
  cleanup();
});

describe('AdminTable', () => {
  it('renders column headers and rows', () => {
    render(<AdminTable<Item> dataSource={data} columns={columns} rowKey="id" />);

    expect(screen.getByText('Name')).toBeDefined();
    expect(screen.getByText('Count')).toBeDefined();
    expect(screen.getByText('Alpha')).toBeDefined();
    expect(screen.getByText('Beta')).toBeDefined();
  });

  it('shows empty text when there is no data', () => {
    render(<AdminTable<Item> dataSource={[]} columns={columns} rowKey="id" emptyText="No items" />);

    expect(screen.getByText('No items')).toBeDefined();
  });

  it('toggles row selection checkboxes', () => {
    const onChange = vi.fn();
    render(
      <AdminTable<Item>
        dataSource={data}
        columns={columns}
        rowKey="id"
        rowSelection={{ selectedRowKeys: [], onChange }}
      />
    );

    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes.length).toBe(3); // header + 2 rows

    fireEvent.click(checkboxes[1]);
    expect(onChange).toHaveBeenCalledWith(['a']);

    fireEvent.click(checkboxes[0]);
    expect(onChange).toHaveBeenCalledWith(['a', 'b']);
  });
});
