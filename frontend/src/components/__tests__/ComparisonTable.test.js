import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ComparisonTable from '../ComparisonTable';

const renderWithRouter = (ui) => render(<MemoryRouter>{ui}</MemoryRouter>);

const sampleProperties = [
  {
    _id: 'p1',
    address: '100 Oak Ave',
    city: 'Dallas',
    state: 'TX',
    price: 275000,
    bedrooms: 3,
    bathrooms: 2,
    sqft: 1600,
    score: 78,
    metrics: { cap_rate: 6.8, monthly_cash_flow: 350 },
  },
  {
    _id: 'p2',
    address: '200 Elm St',
    city: 'Houston',
    state: 'TX',
    price: 185000,
    bedrooms: 2,
    bathrooms: 1,
    sqft: 1200,
    score: 65,
    metrics: { cap_rate: 8.1, monthly_cash_flow: -100 },
  },
];

describe('ComparisonTable', () => {
  it('renders empty state when no properties are provided', () => {
    renderWithRouter(<ComparisonTable properties={[]} />);
    expect(screen.getByText('No properties to compare.')).toBeInTheDocument();
  });

  it('renders empty state when properties is null', () => {
    renderWithRouter(<ComparisonTable properties={null} />);
    expect(screen.getByText('No properties to compare.')).toBeInTheDocument();
  });

  it('renders table headers', () => {
    renderWithRouter(<ComparisonTable properties={sampleProperties} />);
    expect(screen.getByText('Property')).toBeInTheDocument();
    expect(screen.getByText('Price')).toBeInTheDocument();
    expect(screen.getByText('Beds/Baths')).toBeInTheDocument();
    expect(screen.getByText('Sq Ft')).toBeInTheDocument();
    expect(screen.getByText('Cap Rate')).toBeInTheDocument();
    expect(screen.getByText('Cash Flow')).toBeInTheDocument();
    expect(screen.getByText('Score')).toBeInTheDocument();
  });

  it('renders property addresses as links', () => {
    renderWithRouter(<ComparisonTable properties={sampleProperties} />);
    const links = screen.getAllByRole('link');
    expect(links[0]).toHaveAttribute('href', '/property/p1');
    expect(links[0]).toHaveTextContent('100 Oak Ave');
    expect(links[1]).toHaveAttribute('href', '/property/p2');
    expect(links[1]).toHaveTextContent('200 Elm St');
  });

  it('renders city and state for each property', () => {
    renderWithRouter(<ComparisonTable properties={sampleProperties} />);
    expect(screen.getByText('Dallas, TX')).toBeInTheDocument();
    expect(screen.getByText('Houston, TX')).toBeInTheDocument();
  });

  it('renders formatted prices', () => {
    renderWithRouter(<ComparisonTable properties={sampleProperties} />);
    expect(screen.getByText('$275,000')).toBeInTheDocument();
    expect(screen.getByText('$185,000')).toBeInTheDocument();
  });

  it('renders beds/baths combined', () => {
    renderWithRouter(<ComparisonTable properties={sampleProperties} />);
    expect(screen.getByText('3/2')).toBeInTheDocument();
    expect(screen.getByText('2/1')).toBeInTheDocument();
  });

  it('renders cap rates', () => {
    renderWithRouter(<ComparisonTable properties={sampleProperties} />);
    expect(screen.getByText('6.8%')).toBeInTheDocument();
    expect(screen.getByText('8.1%')).toBeInTheDocument();
  });

  it('renders scores', () => {
    renderWithRouter(<ComparisonTable properties={sampleProperties} />);
    expect(screen.getByText('78')).toBeInTheDocument();
    expect(screen.getByText('65')).toBeInTheDocument();
  });

  it('renders a table element', () => {
    renderWithRouter(<ComparisonTable properties={sampleProperties} />);
    expect(screen.getByRole('table')).toBeInTheDocument();
  });

  it('handles properties without metrics', () => {
    const noMetrics = [{ _id: 'p3', address: '300 Pine', city: 'Denver', state: 'CO', price: 400000, bedrooms: 4, bathrooms: 3, sqft: 2200 }];
    renderWithRouter(<ComparisonTable properties={noMetrics} />);
    expect(screen.getByText('300 Pine')).toBeInTheDocument();
  });
});
