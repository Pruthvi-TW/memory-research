import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { DynamicContextDropdown, ContextSource } from '../DynamicContextDropdown';

describe('DynamicContextDropdown', () => {
  const mockOnSourceSelect = jest.fn();

  beforeEach(() => {
    mockOnSourceSelect.mockClear();
  });

  const defaultProps = {
    onSourceSelect: mockOnSourceSelect,
    isProcessing: false,
    disabled: false
  };

  it('renders with default placeholder', () => {
    render(<DynamicContextDropdown {...defaultProps} />);
    
    expect(screen.getByText('Add Dynamic Context')).toBeInTheDocument();
    expect(screen.getByRole('button', { expanded: false })).toBeInTheDocument();
  });

  it('opens dropdown when clicked', () => {
    render(<DynamicContextDropdown {...defaultProps} />);
    
    const trigger = screen.getByRole('button');
    fireEvent.click(trigger);
    
    expect(screen.getByRole('listbox')).toBeInTheDocument();
    expect(screen.getByText('Upload Files')).toBeInTheDocument();
    expect(screen.getByText('Enter URL')).toBeInTheDocument();
    expect(screen.getByText('GitHub Repository')).toBeInTheDocument();
  });

  it('closes dropdown when clicking outside', () => {
    render(<DynamicContextDropdown {...defaultProps} />);
    
    // Open dropdown
    const trigger = screen.getByRole('button');
    fireEvent.click(trigger);
    expect(screen.getByRole('listbox')).toBeInTheDocument();
    
    // Click overlay
    const overlay = document.querySelector('.dropdown-overlay');
    fireEvent.click(overlay!);
    
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });

  it('calls onSourceSelect when option is clicked', () => {
    render(<DynamicContextDropdown {...defaultProps} />);
    
    // Open dropdown
    fireEvent.click(screen.getByRole('button'));
    
    // Click upload option
    fireEvent.click(screen.getByText('Upload Files'));
    
    expect(mockOnSourceSelect).toHaveBeenCalledWith({
      type: 'upload',
      label: 'Upload Files',
      icon: expect.any(Object),
      description: 'Upload PDF, DOCX, TXT, or MD files'
    });
  });

  it('updates selected source display', () => {
    render(<DynamicContextDropdown {...defaultProps} />);
    
    // Open dropdown and select URL option
    fireEvent.click(screen.getByRole('button'));
    fireEvent.click(screen.getByText('Enter URL'));
    
    // Check that selected source is displayed
    expect(screen.getByText('Enter URL')).toBeInTheDocument();
    expect(screen.queryByText('Add Dynamic Context')).not.toBeInTheDocument();
  });

  it('disables dropdown when disabled prop is true', () => {
    render(<DynamicContextDropdown {...defaultProps} disabled={true} />);
    
    const trigger = screen.getByRole('button');
    expect(trigger).toBeDisabled();
    
    fireEvent.click(trigger);
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });

  it('disables dropdown when processing', () => {
    render(<DynamicContextDropdown {...defaultProps} isProcessing={true} />);
    
    const trigger = screen.getByRole('button');
    expect(trigger).toBeDisabled();
    
    fireEvent.click(trigger);
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });

  it('shows correct descriptions for each option', () => {
    render(<DynamicContextDropdown {...defaultProps} />);
    
    fireEvent.click(screen.getByRole('button'));
    
    expect(screen.getByText('Upload PDF, DOCX, TXT, or MD files')).toBeInTheDocument();
    expect(screen.getByText('Extract content from web pages')).toBeInTheDocument();
    expect(screen.getByText('Process documentation from GitHub repos')).toBeInTheDocument();
  });

  it('has proper accessibility attributes', () => {
    render(<DynamicContextDropdown {...defaultProps} />);
    
    const trigger = screen.getByRole('button');
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    expect(trigger).toHaveAttribute('aria-haspopup', 'listbox');
    
    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute('aria-expanded', 'true');
    
    const options = screen.getAllByRole('option');
    expect(options).toHaveLength(3);
    options.forEach(option => {
      expect(option).toHaveAttribute('aria-selected');
    });
  });

  it('applies correct CSS classes based on state', () => {
    render(<DynamicContextDropdown {...defaultProps} />);
    
    const trigger = screen.getByRole('button');
    expect(trigger).toHaveClass('dropdown-trigger');
    expect(trigger).not.toHaveClass('open');
    expect(trigger).not.toHaveClass('disabled');
    
    fireEvent.click(trigger);
    expect(trigger).toHaveClass('open');
  });

  it('rotates arrow icon when dropdown is open', () => {
    render(<DynamicContextDropdown {...defaultProps} />);
    
    const arrow = document.querySelector('.dropdown-arrow');
    expect(arrow).not.toHaveClass('rotated');
    
    fireEvent.click(screen.getByRole('button'));
    expect(arrow).toHaveClass('rotated');
  });
});