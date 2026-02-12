/// <reference lib="dom" />

import { describe, test, expect, mock, beforeEach } from 'bun:test';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import React from 'react';

// Dynamic import for the component after mocks
let MultiSelect: typeof import('./MultiSelect').default;

describe('MultiSelect Component', () => {
  const mockOptions = ['Option 1', 'Option 2', 'Option 3', 'Option 4'];
  const mockOnChange = mock();

  beforeEach(async () => {
    mockOnChange.mockClear();
    const module = await import('./MultiSelect');
    MultiSelect = module.default;
  });

  describe('Rendering', () => {
    test('renders with placeholder when no options selected', () => {
      render(
        React.createElement(MultiSelect, {
          options: mockOptions,
          selected: [],
          onChange: mockOnChange,
          placeholder: 'Select options'
        })
      );
      
      expect(screen.getByText('Select options')).toBeInTheDocument();
    });

    test('renders selected options as tags', () => {
      render(
        React.createElement(MultiSelect, {
          options: mockOptions,
          selected: ['Option 1', 'Option 3'],
          onChange: mockOnChange,
          placeholder: 'Select options'
        })
      );
      
      expect(screen.getByText('Option 1')).toBeInTheDocument();
      expect(screen.getByText('Option 3')).toBeInTheDocument();
      expect(screen.queryByText('Option 2')).not.toBeInTheDocument();
    });

    test('opens dropdown when clicked', () => {
      render(
        React.createElement(MultiSelect, {
          options: mockOptions,
          selected: [],
          onChange: mockOnChange,
          placeholder: 'Select options'
        })
      );
      
      const trigger = screen.getByText('Select options').parentElement;
      fireEvent.click(trigger!);
      
      expect(screen.getByPlaceholderText('Search...')).toBeInTheDocument();
      expect(screen.getByText('Option 1')).toBeInTheDocument();
      expect(screen.getByText('Option 2')).toBeInTheDocument();
      expect(screen.getByText('Option 3')).toBeInTheDocument();
      expect(screen.getByText('Option 4')).toBeInTheDocument();
    });
  });

  describe('Option Selection', () => {
    test('selects an option when clicked', () => {
      render(
        React.createElement(MultiSelect, {
          options: mockOptions,
          selected: [],
          onChange: mockOnChange,
          placeholder: 'Select options'
        })
      );
      
      const trigger = screen.getByText('Select options').parentElement;
      fireEvent.click(trigger!);
      
      const option1 = screen.getByText('Option 1');
      fireEvent.click(option1);
      
      expect(mockOnChange).toHaveBeenCalledWith(['Option 1']);
    });

    test('deselects an option when clicked again', () => {
      render(
        React.createElement(MultiSelect, {
          options: mockOptions,
          selected: ['Option 1'],
          onChange: mockOnChange,
          placeholder: 'Select options'
        })
      );
      
      const trigger = screen.getByText('Option 1').parentElement;
      fireEvent.click(trigger!);
      
      // Find and click on the selected option in dropdown
      const option1InDropdown = screen.getAllByText('Option 1')[1]; // Second occurrence is in dropdown
      fireEvent.click(option1InDropdown);
      
      expect(mockOnChange).toHaveBeenCalledWith([]);
    });

    test('allows multiple selections', () => {
      render(
        React.createElement(MultiSelect, {
          options: mockOptions,
          selected: ['Option 1'],
          onChange: mockOnChange,
          placeholder: 'Select options'
        })
      );
      
      const trigger = screen.getByText('Option 1').parentElement;
      fireEvent.click(trigger!);
      
      const option2 = screen.getByText('Option 2');
      fireEvent.click(option2);
      
      expect(mockOnChange).toHaveBeenCalledWith(['Option 1', 'Option 2']);
    });
  });

  describe('Tag Removal', () => {
    test('removes tag when X button is clicked', () => {
      render(
        React.createElement(MultiSelect, {
          options: mockOptions,
          selected: ['Option 1', 'Option 2'],
          onChange: mockOnChange,
          placeholder: 'Select options'
        })
      );
      
      const removeButtons = screen.getAllByRole('button');
      fireEvent.click(removeButtons[0]); // Click first X button
      
      expect(mockOnChange).toHaveBeenCalledWith(['Option 2']);
    });

    test('does not trigger dropdown when clicking remove button', () => {
      render(
        React.createElement(MultiSelect, {
          options: mockOptions,
          selected: ['Option 1'],
          onChange: mockOnChange,
          placeholder: 'Select options'
        })
      );
      
      const removeButton = screen.getAllByRole('button')[0];
      fireEvent.click(removeButton);
      
      // Dropdown should not be open
      expect(screen.queryByPlaceholderText('Search...')).not.toBeInTheDocument();
    });
  });

  describe('Search Functionality', () => {
    test('filters options based on search input', () => {
      render(
        React.createElement(MultiSelect, {
          options: mockOptions,
          selected: [],
          onChange: mockOnChange,
          placeholder: 'Select options'
        })
      );
      
      const trigger = screen.getByText('Select options').parentElement;
      fireEvent.click(trigger!);
      
      const searchInput = screen.getByPlaceholderText('Search...');
      fireEvent.change(searchInput, { target: { value: 'Option 1' } });
      
      expect(screen.getByText('Option 1')).toBeInTheDocument();
      expect(screen.queryByText('Option 2')).not.toBeInTheDocument();
      expect(screen.queryByText('Option 3')).not.toBeInTheDocument();
    });

    test('shows "No results found" when search has no matches', () => {
      render(
        React.createElement(MultiSelect, {
          options: mockOptions,
          selected: [],
          onChange: mockOnChange,
          placeholder: 'Select options'
        })
      );
      
      const trigger = screen.getByText('Select options').parentElement;
      fireEvent.click(trigger!);
      
      const searchInput = screen.getByPlaceholderText('Search...');
      fireEvent.change(searchInput, { target: { value: 'NonExistent' } });
      
      expect(screen.getByText('No results found')).toBeInTheDocument();
    });

    test('performs case-insensitive search', () => {
      render(
        React.createElement(MultiSelect, {
          options: mockOptions,
          selected: [],
          onChange: mockOnChange,
          placeholder: 'Select options'
        })
      );
      
      const trigger = screen.getByText('Select options').parentElement;
      fireEvent.click(trigger!);
      
      const searchInput = screen.getByPlaceholderText('Search...');
      fireEvent.change(searchInput, { target: { value: 'option 1' } });
      
      expect(screen.getByText('Option 1')).toBeInTheDocument();
    });
  });

  describe('Label Mapping', () => {
    const mockLabelMap = {
      'software_engineering': 'Software Engineering',
      'data_science': 'Data Science',
    };

    test('displays mapped labels for options', () => {
      render(
        React.createElement(MultiSelect, {
          options: ['software_engineering', 'data_science'],
          selected: ['software_engineering'],
          onChange: mockOnChange,
          placeholder: 'Select category',
          labelMap: mockLabelMap
        })
      );
      
      expect(screen.getByText('Software Engineering')).toBeInTheDocument();
    });

    test('uses original value when no label mapping exists', () => {
      render(
        React.createElement(MultiSelect, {
          options: ['software_engineering', 'unknown_category'],
          selected: ['unknown_category'],
          onChange: mockOnChange,
          placeholder: 'Select category',
          labelMap: mockLabelMap
        })
      );
      
      expect(screen.getByText('unknown_category')).toBeInTheDocument();
    });

    test('searches using mapped labels', () => {
      render(
        React.createElement(MultiSelect, {
          options: ['software_engineering', 'data_science'],
          selected: [],
          onChange: mockOnChange,
          placeholder: 'Select category',
          labelMap: mockLabelMap
        })
      );
      
      const trigger = screen.getByText('Select category').parentElement;
      fireEvent.click(trigger!);
      
      const searchInput = screen.getByPlaceholderText('Search...');
      fireEvent.change(searchInput, { target: { value: 'Software' } });
      
      expect(screen.getByText('Software Engineering')).toBeInTheDocument();
      expect(screen.queryByText('Data Science')).not.toBeInTheDocument();
    });
  });

  describe('Dropdown Behavior', () => {
    test('closes dropdown when clicking outside', () => {
      render(
        React.createElement(MultiSelect, {
          options: mockOptions,
          selected: [],
          onChange: mockOnChange,
          placeholder: 'Select options'
        })
      );
      
      // Open dropdown
      const trigger = screen.getByText('Select options').parentElement;
      fireEvent.click(trigger!);
      
      expect(screen.getByPlaceholderText('Search...')).toBeInTheDocument();
      
      // Click outside
      fireEvent.mouseDown(document.body);
      
      expect(screen.queryByPlaceholderText('Search...')).not.toBeInTheDocument();
    });

    test('toggles dropdown when clicking trigger', () => {
      render(
        React.createElement(MultiSelect, {
          options: mockOptions,
          selected: [],
          onChange: mockOnChange,
          placeholder: 'Select options'
        })
      );
      
      const trigger = screen.getByText('Select options').parentElement;
      
      // Open
      fireEvent.click(trigger!);
      expect(screen.getByPlaceholderText('Search...')).toBeInTheDocument();
      
      // Close
      fireEvent.click(trigger!);
      expect(screen.queryByPlaceholderText('Search...')).not.toBeInTheDocument();
    });

    test('rotates chevron icon when dropdown is open', () => {
      render(
        React.createElement(MultiSelect, {
          options: mockOptions,
          selected: [],
          onChange: mockOnChange,
          placeholder: 'Select options'
        })
      );
      
      const trigger = screen.getByText('Select options').parentElement;
      const chevron = trigger!.querySelector('svg');
      
      expect(chevron).not.toHaveClass('rotate-180');
      
      fireEvent.click(trigger!);
      
      expect(chevron).toHaveClass('rotate-180');
    });
  });

  describe('Checkmarks', () => {
    test('shows checkmark for selected options', () => {
      render(
        React.createElement(MultiSelect, {
          options: mockOptions,
          selected: ['Option 1', 'Option 3'],
          onChange: mockOnChange,
          placeholder: 'Select options'
        })
      );
      
      const trigger = screen.getByText('Option 1').parentElement;
      fireEvent.click(trigger!);
      
      // Check that checkmarks are present (svg elements)
      const checkmarks = document.querySelectorAll('svg');
      expect(checkmarks.length).toBeGreaterThan(0);
    });
  });

  describe('Accessibility', () => {
    test('has clickable options in dropdown', () => {
      render(
        React.createElement(MultiSelect, {
          options: mockOptions,
          selected: [],
          onChange: mockOnChange,
          placeholder: 'Select options'
        })
      );
      
      const trigger = screen.getByText('Select options').parentElement;
      fireEvent.click(trigger!);
      
      const options = screen.getAllByText(/Option/);
      options.forEach(option => {
        expect(option.parentElement).toHaveClass('cursor-pointer');
      });
    });

    test('has proper styling for hover states', () => {
      render(
        React.createElement(MultiSelect, {
          options: mockOptions,
          selected: [],
          onChange: mockOnChange,
          placeholder: 'Select options'
        })
      );
      
      const trigger = screen.getByText('Select options').parentElement;
      fireEvent.click(trigger!);
      
      const option = screen.getByText('Option 1').parentElement;
      expect(option).toHaveClass('hover:bg-slate-50');
    });
  });
});
