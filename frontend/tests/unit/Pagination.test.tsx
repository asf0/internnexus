import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import Pagination from '@/components/ui/Pagination';

afterEach(() => {
  cleanup();
});

const buildPageUrl = (page: number) => `/?page=${page}`;

describe('Pagination', () => {
  it('hides Previous on the first page', () => {
    render(<Pagination currentPage={1} totalPages={4} buildPageUrl={buildPageUrl} />);

    expect(screen.queryByText('Previous')).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Go to page 2' })).toHaveAttribute('href', '/?page=2');
    expect(screen.getByText('Page 1')).toBeInTheDocument();
    expect(screen.queryByText(/of 4/)).not.toBeInTheDocument();
  });

  it('shows both directions on a middle page', () => {
    render(<Pagination currentPage={2} totalPages={4} buildPageUrl={buildPageUrl} />);

    expect(screen.getByText('Previous')).toBeInTheDocument();
    expect(screen.getByText('Next')).toBeInTheDocument();
  });

  it('hides Next on the last page', () => {
    render(<Pagination currentPage={4} totalPages={4} buildPageUrl={buildPageUrl} />);

    expect(screen.getByRole('link', { name: 'Go to page 3' })).toHaveAttribute('href', '/?page=3');
    expect(screen.queryByText('Next')).not.toBeInTheDocument();
    expect(screen.getByText('Page 4')).toBeInTheDocument();
  });

  it('hides pagination when only one page exists', () => {
    render(<Pagination currentPage={1} totalPages={1} buildPageUrl={buildPageUrl} />);

    expect(screen.queryByRole('navigation', { name: 'Pagination' })).not.toBeInTheDocument();
  });
});
