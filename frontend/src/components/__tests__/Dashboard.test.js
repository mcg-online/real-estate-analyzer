import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Dashboard from '../Dashboard';
import api from '../../services/api';

const renderWithRouter = (ui) => render(<MemoryRouter>{ui}</MemoryRouter>);

const mockProperties = [
  {
    _id: 'p1',
    address: '100 Oak Ave',
    city: 'Austin',
    state: 'TX',
    price: 300000,
    bedrooms: 3,
    bathrooms: 2,
    sqft: 1800,
    score: 85,
    metrics: { cap_rate: 7.0, monthly_cash_flow: 400, cash_on_cash_return: 8, roi: { annualized_roi: 12 } },
  },
  {
    _id: 'p2',
    address: '200 Elm St',
    city: 'Dallas',
    state: 'TX',
    price: 200000,
    bedrooms: 2,
    bathrooms: 1,
    sqft: 1200,
    score: 70,
    metrics: { cap_rate: 6.0, monthly_cash_flow: 300, cash_on_cash_return: 7, roi: { annualized_roi: 10 } },
  },
];

const mockMarkets = [
  { name: 'Austin, TX', avg_roi: 15.0, avg_cap_rate: 7.5, avg_price: 320000 },
];

describe('Dashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    // Re-setup Leaflet mock implementations after clearAllMocks wipes them
    // (Dashboard renders MapView which needs these)
    const L = require('leaflet');
    const markerInstance = {
      addTo: jest.fn().mockReturnThis(),
      bindPopup: jest.fn().mockReturnThis(),
      remove: jest.fn(),
    };
    const mapInstance = {
      setView: jest.fn().mockReturnThis(),
      remove: jest.fn(),
      eachLayer: jest.fn(),
      removeLayer: jest.fn(),
      fitBounds: jest.fn(),
    };
    const tileLayerInstance = { addTo: jest.fn() };

    L.map.mockReturnValue(mapInstance);
    L.tileLayer.mockReturnValue(tileLayerInstance);
    L.marker.mockReturnValue(markerInstance);
    L.divIcon.mockImplementation((opts) => opts);
  });

  it('shows loading state initially', () => {
    // Make the API call hang
    api.getProperties.mockReturnValue(new Promise(() => {}));
    api.getTopMarkets.mockReturnValue(new Promise(() => {}));

    renderWithRouter(<Dashboard />);
    expect(screen.getByText('Loading dashboard...')).toBeInTheDocument();
  });

  it('renders dashboard content after successful data fetch', async () => {
    api.getProperties.mockResolvedValue({ data: { data: mockProperties } });
    api.getTopMarkets.mockResolvedValue({ data: mockMarkets });

    renderWithRouter(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('Investment Dashboard')).toBeInTheDocument();
    });

    expect(screen.getByText('Top Investment Opportunities')).toBeInTheDocument();
    expect(screen.getByText('Filter Properties')).toBeInTheDocument();
    expect(screen.getByText('Property Map')).toBeInTheDocument();
    expect(screen.getByText('Investment Summary')).toBeInTheDocument();
    expect(screen.getByText('Top Markets by ROI')).toBeInTheDocument();
    expect(screen.getByText('Investment Metrics')).toBeInTheDocument();
  });

  it('renders summary statistics labels', async () => {
    api.getProperties.mockResolvedValue({ data: { data: mockProperties } });
    api.getTopMarkets.mockResolvedValue({ data: mockMarkets });

    renderWithRouter(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('Investment Dashboard')).toBeInTheDocument();
    });

    // Stat labels from the Dashboard summary grid (some also appear in TopMarketsTable)
    expect(screen.getByText('Properties')).toBeInTheDocument();
    expect(screen.getAllByText('Avg. Price').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Avg. ROI').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Avg. Cap Rate').length).toBeGreaterThanOrEqual(1);
  });

  it('renders computed average price value', async () => {
    api.getProperties.mockResolvedValue({ data: { data: mockProperties } });
    api.getTopMarkets.mockResolvedValue({ data: mockMarkets });

    renderWithRouter(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('Investment Dashboard')).toBeInTheDocument();
    });

    // Average price appears in both Dashboard stats and InvestmentSummary
    const avgPriceElements = screen.getAllByText('$250,000');
    expect(avgPriceElements.length).toBeGreaterThanOrEqual(1);
  });

  it('shows error state when API fails', async () => {
    api.getProperties.mockRejectedValue(new Error('Network error'));
    api.getTopMarkets.mockRejectedValue(new Error('Network error'));

    renderWithRouter(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('Failed to fetch data. Please try again later.')).toBeInTheDocument();
    });
  });

  it('shows empty properties message when no properties match', async () => {
    api.getProperties.mockResolvedValue({ data: { data: [] } });
    api.getTopMarkets.mockResolvedValue({ data: [] });

    renderWithRouter(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('No properties match your current filters.')).toBeInTheDocument();
    });
  });

  it('renders PropertyCard components for top properties', async () => {
    api.getProperties.mockResolvedValue({ data: { data: mockProperties } });
    api.getTopMarkets.mockResolvedValue({ data: mockMarkets });

    renderWithRouter(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('100 Oak Ave')).toBeInTheDocument();
    });
    expect(screen.getByText('200 Elm St')).toBeInTheDocument();
  });

  it('renders View all properties link', async () => {
    api.getProperties.mockResolvedValue({ data: { data: mockProperties } });
    api.getTopMarkets.mockResolvedValue({ data: mockMarkets });

    renderWithRouter(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('Investment Dashboard')).toBeInTheDocument();
    });

    const viewAllLinks = screen.getAllByRole('link');
    const viewPropertiesLink = viewAllLinks.find(link => link.textContent.includes('View all properties'));
    expect(viewPropertiesLink).toBeInTheDocument();
  });

  it('passes correct filter params to API', async () => {
    api.getProperties.mockResolvedValue({ data: { data: [] } });
    api.getTopMarkets.mockResolvedValue({ data: [] });

    renderWithRouter(<Dashboard />);

    await waitFor(() => {
      expect(api.getProperties).toHaveBeenCalled();
    });

    // Default filters only include minScore: 70 (others are empty strings filtered out)
    expect(api.getProperties).toHaveBeenCalledWith({ minScore: 70 });
  });
});
