import React from 'react';
import { render, screen } from '@testing-library/react';
import Toolbar from './Toolbar';

describe('Toolbar Component', () => {
  it('renders without crashing', () => {
    render(<Toolbar />);
    expect(screen.getByText(/search/i)).toBeInTheDocument();
  });

  it('displays the correct title', () => {
    render(<Toolbar />);
    expect(screen.getByText(/intern nexus/i)).toBeInTheDocument();
  });
});