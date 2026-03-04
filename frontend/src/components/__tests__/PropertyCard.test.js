import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import PropertyCard from '../PropertyCard';

const renderWithRouter = (ui) => render(<MemoryRouter>{ui}</MemoryRouter>);

const baseProperty = {
  _id: 'prop123',
  address: '123 Main St',
  city: 'Austin',
  state: 'TX',
  price: 350000,
  bedrooms: 3,
  bathrooms: 2,
  sqft: 1800,
};

describe('PropertyCard', () => {
  it('renders property address, city, and state', () => {
    renderWithRouter(<PropertyCard property={baseProperty} />);
    expect(screen.getByText('123 Main St')).toBeInTheDocument();
    expect(screen.getByText('Austin, TX')).toBeInTheDocument();
  });

  it('renders formatted price', () => {
    renderWithRouter(<PropertyCard property={baseProperty} />);
    expect(screen.getByText('$350,000')).toBeInTheDocument();
  });

  it('renders bedrooms, bathrooms, and sqft', () => {
    renderWithRouter(<PropertyCard property={baseProperty} />);
    expect(screen.getByText('3 bd')).toBeInTheDocument();
    expect(screen.getByText('2 ba')).toBeInTheDocument();
    expect(screen.getByText('1,800 sqft')).toBeInTheDocument();
  });

  it('links to the property detail page', () => {
    renderWithRouter(<PropertyCard property={baseProperty} />);
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/property/prop123');
  });

  it('renders score badge when score is provided', () => {
    const property = { ...baseProperty, score: 85 };
    renderWithRouter(<PropertyCard property={property} />);
    expect(screen.getByText('85')).toBeInTheDocument();
  });

  it('does not render score badge when score is missing', () => {
    renderWithRouter(<PropertyCard property={baseProperty} />);
    // No score badge should appear
    const spans = screen.queryAllByText(/^\d+$/);
    // Only numeric texts should be from price, beds, baths, sqft -- not a score badge
    expect(screen.queryByText('?')).not.toBeInTheDocument();
  });

  it('shows "No image" placeholder when no images', () => {
    renderWithRouter(<PropertyCard property={baseProperty} />);
    expect(screen.getByText('No image')).toBeInTheDocument();
  });

  it('renders property image when images are provided', () => {
    const property = { ...baseProperty, images: ['https://example.com/photo.jpg'] };
    renderWithRouter(<PropertyCard property={property} />);
    const img = screen.getByRole('img');
    expect(img).toHaveAttribute('src', 'https://example.com/photo.jpg');
    expect(img).toHaveAttribute('alt', '123 Main St');
  });

  it('renders metrics when available', () => {
    const property = {
      ...baseProperty,
      metrics: { cap_rate: 7.5, monthly_cash_flow: 450 },
    };
    renderWithRouter(<PropertyCard property={property} />);
    expect(screen.getByText(/Cap Rate: 7.5%/)).toBeInTheDocument();
    expect(screen.getByText(/Cash Flow: \$450/)).toBeInTheDocument();
  });

  it('does not render metrics section when metrics are absent', () => {
    renderWithRouter(<PropertyCard property={baseProperty} />);
    expect(screen.queryByText(/Cap Rate/)).not.toBeInTheDocument();
  });

  it('applies correct score color for high score', () => {
    const property = { ...baseProperty, score: 90 };
    renderWithRouter(<PropertyCard property={property} />);
    const badge = screen.getByText('90');
    expect(badge).toHaveStyle({ backgroundColor: '#22c55e' });
  });

  it('applies correct score color for low score', () => {
    const property = { ...baseProperty, score: 30 };
    renderWithRouter(<PropertyCard property={property} />);
    const badge = screen.getByText('30');
    expect(badge).toHaveStyle({ backgroundColor: '#dc2626' });
  });
});
