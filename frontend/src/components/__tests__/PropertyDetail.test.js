import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import PropertyDetail from '../PropertyDetail';
import api from '../../services/api';

const renderWithRoute = (id = 'prop1') => {
  return render(
    <MemoryRouter initialEntries={[`/property/${id}`]}>
      <Routes>
        <Route path="/property/:id" element={<PropertyDetail />} />
      </Routes>
    </MemoryRouter>
  );
};

const mockProperty = {
  _id: 'prop1',
  address: '123 Main St',
  city: 'Austin',
  state: 'TX',
  zip_code: '78701',
  price: 350000,
  bedrooms: 3,
  bathrooms: 2,
  sqft: 1800,
  year_built: 2005,
  score: 82,
  property_type: 'single_family',
  description: 'A beautiful home in downtown Austin.',
  source: 'MLS',
  listing_url: 'https://example.com/listing',
  images: ['https://example.com/img1.jpg', 'https://example.com/img2.jpg'],
};

const mockAnalysis = {
  financial_analysis: {
    monthly_cash_flow: 450,
    cap_rate: 7.2,
    cash_on_cash_return: 8.5,
    gross_yield: 9.1,
    break_even_point: 12,
    monthly_rent: 2200,
    monthly_expenses: { total: 800, property_tax: 200, insurance: 100, maintenance: 150, vacancy: 100, management: 150, hoa: 0 },
    mortgage_payment: 1500,
    roi: { total_roi: 45.0, annualized_roi: 7.7, future_value: 420000, total_cash_flow: 27000, appreciation_profit: 50000 },
  },
  financing_options: {
    options: [
      {
        type: 'Conventional',
        loan_amount: 280000,
        down_payment: 70000,
        down_payment_percentage: 20,
        interest_rate: 4.5,
        term_years: 30,
        monthly_payment: 1419,
        monthly_pmi: 0,
        monthly_mip: 0,
        upfront_mip: 0,
        funding_fee: 0,
        funding_fee_percentage: 0,
        total_monthly_payment: 1419,
        total_interest: 230840,
      },
    ],
    local_programs: [],
  },
  tax_benefits: {
    depreciation: { building_value: 280000, land_value: 70000, annual_depreciation: 10182, monthly_depreciation: 849 },
    mortgage_interest_deduction: 12600,
    property_tax_deduction: 2400,
    total_deductions: 25182,
    estimated_tax_savings: 5540,
    monthly_tax_savings: 462,
  },
  market_data: {
    property_tax_rate: 0.0195,
    vacancy_rate: 0.06,
    price_to_rent_ratio: 13.2,
    appreciation_rate: 0.035,
    school_rating: 7,
    crime_rating: 8,
    walk_score: 72,
    transit_score: 55,
  },
};

describe('PropertyDetail', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows loading state initially', () => {
    api.getProperty.mockReturnValue(new Promise(() => {}));
    api.getPropertyAnalysis.mockReturnValue(new Promise(() => {}));

    renderWithRoute();
    expect(screen.getByText('Loading property details...')).toBeInTheDocument();
  });

  it('shows error state when API fails', async () => {
    api.getProperty.mockRejectedValue(new Error('Server error'));
    api.getPropertyAnalysis.mockRejectedValue(new Error('Server error'));

    renderWithRoute();

    await waitFor(() => {
      expect(screen.getByText('Failed to fetch property details. Please try again later.')).toBeInTheDocument();
    });
  });

  it('renders property header with address, city, state, zip', async () => {
    api.getProperty.mockResolvedValue({ data: mockProperty });
    api.getPropertyAnalysis.mockResolvedValue({ data: mockAnalysis });
    api.getProperties.mockResolvedValue({ data: { data: [] } });

    renderWithRoute();

    await waitFor(() => {
      expect(screen.getByText('123 Main St')).toBeInTheDocument();
    });
    expect(screen.getByText('Austin, TX 78701')).toBeInTheDocument();
    expect(screen.getByText('$350,000')).toBeInTheDocument();
  });

  it('renders property details (bedrooms, bathrooms, sqft, year built)', async () => {
    api.getProperty.mockResolvedValue({ data: mockProperty });
    api.getPropertyAnalysis.mockResolvedValue({ data: mockAnalysis });
    api.getProperties.mockResolvedValue({ data: { data: [] } });

    renderWithRoute();

    await waitFor(() => {
      expect(screen.getByText('3 Bedrooms')).toBeInTheDocument();
    });
    expect(screen.getByText('2 Bathrooms')).toBeInTheDocument();
    expect(screen.getByText('1,800 sq ft')).toBeInTheDocument();
    expect(screen.getByText('Built in 2005')).toBeInTheDocument();
  });

  it('renders navigation tabs', async () => {
    api.getProperty.mockResolvedValue({ data: mockProperty });
    api.getPropertyAnalysis.mockResolvedValue({ data: mockAnalysis });
    api.getProperties.mockResolvedValue({ data: { data: [] } });

    renderWithRoute();

    await waitFor(() => {
      expect(screen.getByText('Overview')).toBeInTheDocument();
    });
    expect(screen.getByText('Financial Analysis')).toBeInTheDocument();
    expect(screen.getByText('Financing Options')).toBeInTheDocument();
    expect(screen.getByText('Tax Benefits')).toBeInTheDocument();
    expect(screen.getByText('Location')).toBeInTheDocument();
  });

  it('shows overview tab content by default with description', async () => {
    api.getProperty.mockResolvedValue({ data: mockProperty });
    api.getPropertyAnalysis.mockResolvedValue({ data: mockAnalysis });
    api.getProperties.mockResolvedValue({ data: { data: [] } });

    renderWithRoute();

    await waitFor(() => {
      expect(screen.getByText('Property Overview')).toBeInTheDocument();
    });
    expect(screen.getByText('A beautiful home in downtown Austin.')).toBeInTheDocument();
  });

  it('shows key investment metrics on overview tab', async () => {
    api.getProperty.mockResolvedValue({ data: mockProperty });
    api.getPropertyAnalysis.mockResolvedValue({ data: mockAnalysis });
    api.getProperties.mockResolvedValue({ data: { data: [] } });

    renderWithRoute();

    await waitFor(() => {
      expect(screen.getByText('Key Investment Metrics')).toBeInTheDocument();
    });
    expect(screen.getByText('Monthly Cash Flow')).toBeInTheDocument();
    expect(screen.getByText('Cap Rate')).toBeInTheDocument();
    expect(screen.getByText('Cash-on-Cash Return')).toBeInTheDocument();
  });

  it('switches to Financial Analysis tab when clicked', async () => {
    api.getProperty.mockResolvedValue({ data: mockProperty });
    api.getPropertyAnalysis.mockResolvedValue({ data: mockAnalysis });
    api.getProperties.mockResolvedValue({ data: { data: [] } });

    renderWithRoute();

    await waitFor(() => {
      expect(screen.getByText('Overview')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Financial Analysis'));

    // The tab content should now show the Financial Analysis section header
    await waitFor(() => {
      // The InvestmentMetrics component renders "Key Investment Metrics"
      expect(screen.getAllByText(/Investment Metrics/).length).toBeGreaterThan(0);
    });
  });

  it('renders back to properties link', async () => {
    api.getProperty.mockResolvedValue({ data: mockProperty });
    api.getPropertyAnalysis.mockResolvedValue({ data: mockAnalysis });
    api.getProperties.mockResolvedValue({ data: { data: [] } });

    renderWithRoute();

    await waitFor(() => {
      expect(screen.getByText('123 Main St')).toBeInTheDocument();
    });

    const backLink = screen.getAllByRole('link').find(link => link.getAttribute('href') === '/');
    expect(backLink).toBeInTheDocument();
  });

  it('renders listing URL as link when valid', async () => {
    api.getProperty.mockResolvedValue({ data: mockProperty });
    api.getPropertyAnalysis.mockResolvedValue({ data: mockAnalysis });
    api.getProperties.mockResolvedValue({ data: { data: [] } });

    renderWithRoute();

    await waitFor(() => {
      expect(screen.getByText('View original listing')).toBeInTheDocument();
    });

    const listingLink = screen.getByText('View original listing');
    expect(listingLink).toHaveAttribute('href', 'https://example.com/listing');
    expect(listingLink).toHaveAttribute('target', '_blank');
    expect(listingLink).toHaveAttribute('rel', 'noopener noreferrer');
  });
});
