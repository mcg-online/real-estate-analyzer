import React from 'react';
import { render, screen } from '@testing-library/react';
import TopMarketsTable from '../TopMarketsTable';

const sampleMarkets = [
  { name: 'Austin, TX', avg_roi: 15.25, avg_cap_rate: 7.80, avg_price: 320000 },
  { name: 'Nashville, TN', avg_roi: 12.50, avg_cap_rate: 6.90, avg_price: 280000 },
  { market_name: 'Denver, CO', avg_roi: 10.00, avg_cap_rate: 5.50, avg_price: 450000 },
];

describe('TopMarketsTable', () => {
  it('renders empty state when no markets are provided', () => {
    render(<TopMarketsTable markets={[]} />);
    expect(screen.getByText('No market data available.')).toBeInTheDocument();
  });

  it('renders empty state when markets is null', () => {
    render(<TopMarketsTable markets={null} />);
    expect(screen.getByText('No market data available.')).toBeInTheDocument();
  });

  it('renders table headers', () => {
    render(<TopMarketsTable markets={sampleMarkets} />);
    expect(screen.getByText('Rank')).toBeInTheDocument();
    expect(screen.getByText('Market')).toBeInTheDocument();
    expect(screen.getByText('Avg. ROI')).toBeInTheDocument();
    expect(screen.getByText('Cap Rate')).toBeInTheDocument();
    expect(screen.getByText('Avg. Price')).toBeInTheDocument();
  });

  it('renders rank numbers starting from 1', () => {
    render(<TopMarketsTable markets={sampleMarkets} />);
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('renders market names using name or market_name fallback', () => {
    render(<TopMarketsTable markets={sampleMarkets} />);
    expect(screen.getByText('Austin, TX')).toBeInTheDocument();
    expect(screen.getByText('Nashville, TN')).toBeInTheDocument();
    expect(screen.getByText('Denver, CO')).toBeInTheDocument();
  });

  it('renders formatted ROI percentages', () => {
    render(<TopMarketsTable markets={sampleMarkets} />);
    expect(screen.getByText('15.25%')).toBeInTheDocument();
    expect(screen.getByText('12.50%')).toBeInTheDocument();
    expect(screen.getByText('10.00%')).toBeInTheDocument();
  });

  it('renders formatted cap rates', () => {
    render(<TopMarketsTable markets={sampleMarkets} />);
    expect(screen.getByText('7.80%')).toBeInTheDocument();
    expect(screen.getByText('6.90%')).toBeInTheDocument();
    expect(screen.getByText('5.50%')).toBeInTheDocument();
  });

  it('renders formatted average prices', () => {
    render(<TopMarketsTable markets={sampleMarkets} />);
    expect(screen.getByText('$320,000')).toBeInTheDocument();
    expect(screen.getByText('$280,000')).toBeInTheDocument();
    expect(screen.getByText('$450,000')).toBeInTheDocument();
  });

  it('renders a table element', () => {
    render(<TopMarketsTable markets={sampleMarkets} />);
    expect(screen.getByRole('table')).toBeInTheDocument();
  });

  it('falls back to Market N when no name or market_name', () => {
    const noName = [{ avg_roi: 5.0, avg_cap_rate: 4.0, avg_price: 150000 }];
    render(<TopMarketsTable markets={noName} />);
    expect(screen.getByText('Market 1')).toBeInTheDocument();
  });
});
