import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import FilterPanel from '../FilterPanel';

const defaultFilters = {
  minPrice: '',
  maxPrice: '',
  minBedrooms: '',
  minBathrooms: '',
  propertyType: '',
  minScore: 70,
};

describe('FilterPanel', () => {
  it('renders all filter fields', () => {
    const onChange = jest.fn();
    render(<FilterPanel filters={defaultFilters} onFilterChange={onChange} />);

    expect(screen.getByLabelText('Minimum price in dollars')).toBeInTheDocument();
    expect(screen.getByLabelText('Maximum price in dollars')).toBeInTheDocument();
    expect(screen.getByLabelText('Min Bedrooms')).toBeInTheDocument();
    expect(screen.getByLabelText('Min Bathrooms')).toBeInTheDocument();
    expect(screen.getByLabelText('Property Type')).toBeInTheDocument();
  });

  it('has a form role with proper aria-label', () => {
    const onChange = jest.fn();
    render(<FilterPanel filters={defaultFilters} onFilterChange={onChange} />);

    expect(screen.getByRole('form', { name: 'Property filters' })).toBeInTheDocument();
  });

  it('has ARIA groups for price range and rooms', () => {
    const onChange = jest.fn();
    render(<FilterPanel filters={defaultFilters} onFilterChange={onChange} />);

    // Price range group
    expect(screen.getByRole('group', { name: 'Price Range' })).toBeInTheDocument();
    // Room requirements group
    expect(screen.getByRole('group', { name: 'Room Requirements' })).toBeInTheDocument();
  });

  it('renders the min score slider with correct ARIA attributes', () => {
    const onChange = jest.fn();
    render(<FilterPanel filters={defaultFilters} onFilterChange={onChange} />);

    const slider = screen.getByRole('slider');
    expect(slider).toHaveAttribute('aria-valuemin', '0');
    expect(slider).toHaveAttribute('aria-valuemax', '100');
    expect(slider).toHaveAttribute('aria-valuenow', '70');
  });

  it('calls onFilterChange when min price changes', () => {
    const onChange = jest.fn();
    render(<FilterPanel filters={defaultFilters} onFilterChange={onChange} />);

    const minPriceInput = screen.getByLabelText('Minimum price in dollars');
    fireEvent.change(minPriceInput, { target: { name: 'minPrice', value: '200000' } });

    expect(onChange).toHaveBeenCalledWith({ minPrice: '200000' });
  });

  it('calls onFilterChange when max price changes', () => {
    const onChange = jest.fn();
    render(<FilterPanel filters={defaultFilters} onFilterChange={onChange} />);

    const maxPriceInput = screen.getByLabelText('Maximum price in dollars');
    fireEvent.change(maxPriceInput, { target: { name: 'maxPrice', value: '500000' } });

    expect(onChange).toHaveBeenCalledWith({ maxPrice: '500000' });
  });

  it('calls onFilterChange when bedroom selection changes', () => {
    const onChange = jest.fn();
    render(<FilterPanel filters={defaultFilters} onFilterChange={onChange} />);

    const bedroomSelect = screen.getByLabelText('Min Bedrooms');
    fireEvent.change(bedroomSelect, { target: { name: 'minBedrooms', value: '3' } });

    expect(onChange).toHaveBeenCalledWith({ minBedrooms: '3' });
  });

  it('calls onFilterChange when property type changes', () => {
    const onChange = jest.fn();
    render(<FilterPanel filters={defaultFilters} onFilterChange={onChange} />);

    const typeSelect = screen.getByLabelText('Property Type');
    fireEvent.change(typeSelect, { target: { name: 'propertyType', value: 'Condo' } });

    expect(onChange).toHaveBeenCalledWith({ propertyType: 'Condo' });
  });

  it('shows results count when provided (plural)', () => {
    const onChange = jest.fn();
    render(<FilterPanel filters={defaultFilters} onFilterChange={onChange} resultsCount={15} />);

    expect(screen.getByText('15 properties found.')).toBeInTheDocument();
  });

  it('shows results count for singular', () => {
    const onChange = jest.fn();
    render(<FilterPanel filters={defaultFilters} onFilterChange={onChange} resultsCount={1} />);

    expect(screen.getByText('1 property found.')).toBeInTheDocument();
  });

  it('shows no results message when count is zero', () => {
    const onChange = jest.fn();
    render(<FilterPanel filters={defaultFilters} onFilterChange={onChange} resultsCount={0} />);

    expect(screen.getByText('No properties match your filters.')).toBeInTheDocument();
  });

  it('has an aria-live polite region for results count', () => {
    const onChange = jest.fn();
    render(<FilterPanel filters={defaultFilters} onFilterChange={onChange} resultsCount={5} />);

    const liveRegion = screen.getByText('5 properties found.');
    expect(liveRegion).toHaveAttribute('aria-live', 'polite');
    expect(liveRegion).toHaveAttribute('aria-atomic', 'true');
  });

  it('resets filters when Reset Filters button is clicked', () => {
    const onChange = jest.fn();
    render(<FilterPanel filters={defaultFilters} onFilterChange={onChange} />);

    const resetButton = screen.getByRole('button', { name: 'Reset all filters to default values' });
    fireEvent.click(resetButton);

    expect(onChange).toHaveBeenCalledWith({
      minPrice: '',
      maxPrice: '',
      minBedrooms: '',
      minBathrooms: '',
      propertyType: '',
      minScore: 70,
    });
  });

  it('does not show results count when resultsCount is undefined', () => {
    const onChange = jest.fn();
    render(<FilterPanel filters={defaultFilters} onFilterChange={onChange} />);

    expect(screen.queryByText(/properties found/)).not.toBeInTheDocument();
    expect(screen.queryByText(/No properties match/)).not.toBeInTheDocument();
  });
});
