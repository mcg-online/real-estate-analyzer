import React from 'react';
import { render, screen } from '@testing-library/react';
import MarketMetricsChart from '../MarketMetricsChart';

const propertiesWithMetrics = [
  {
    _id: '1',
    city: 'Austin',
    metrics: {
      cap_rate: 7.0,
      cash_on_cash_return: 8.5,
      roi: { annualized_roi: 12.0 },
      monthly_cash_flow: 450,
    },
  },
  {
    _id: '2',
    city: 'Austin',
    metrics: {
      cap_rate: 6.0,
      cash_on_cash_return: 7.0,
      roi: { annualized_roi: 10.0 },
      monthly_cash_flow: 300,
    },
  },
  {
    _id: '3',
    city: 'Dallas',
    metrics: {
      cap_rate: 8.0,
      cash_on_cash_return: 9.0,
      roi: { annualized_roi: 14.0 },
      monthly_cash_flow: 600,
    },
  },
];

describe('MarketMetricsChart', () => {
  it('renders empty state when no properties with metrics', () => {
    render(<MarketMetricsChart properties={[]} />);
    expect(screen.getByText('No properties with complete metrics data available.')).toBeInTheDocument();
  });

  it('renders empty state when properties have incomplete metrics', () => {
    const noMetrics = [{ _id: '1', city: 'Test', metrics: { cap_rate: 5 } }];
    render(<MarketMetricsChart properties={noMetrics} />);
    // Missing cash_on_cash_return and roi, so should show empty state
    expect(screen.getByText('No properties with complete metrics data available.')).toBeInTheDocument();
  });

  it('renders the mock Bar chart when valid properties are provided', () => {
    render(<MarketMetricsChart properties={propertiesWithMetrics} />);
    expect(screen.getByTestId('mock-bar-chart')).toBeInTheDocument();
  });

  it('groups properties by city and passes labels to chart', () => {
    render(<MarketMetricsChart properties={propertiesWithMetrics} />);
    const chartElement = screen.getByTestId('mock-bar-chart');
    // The mock Bar renders labels as JSON -- check that city names appear
    expect(chartElement.textContent).toContain('Dallas');
    expect(chartElement.textContent).toContain('Austin');
  });

  it('sorts cities by average cap rate descending', () => {
    render(<MarketMetricsChart properties={propertiesWithMetrics} />);
    const chartElement = screen.getByTestId('mock-bar-chart');
    const text = chartElement.textContent;
    // Dallas has cap_rate 8.0, Austin avg 6.5 -- Dallas should come first
    const dallasIndex = text.indexOf('Dallas');
    const austinIndex = text.indexOf('Austin');
    expect(dallasIndex).toBeLessThan(austinIndex);
  });

  it('renders with correct container height', () => {
    const { container } = render(<MarketMetricsChart properties={propertiesWithMetrics} />);
    const chartContainer = container.firstChild;
    expect(chartContainer).toHaveStyle({ height: '400px', width: '100%' });
  });

  it('handles properties without city gracefully (uses Unknown)', () => {
    const noCityProps = [
      { _id: '1', metrics: { cap_rate: 5, cash_on_cash_return: 6, roi: { annualized_roi: 7 }, monthly_cash_flow: 200 } },
    ];
    render(<MarketMetricsChart properties={noCityProps} />);
    const chartElement = screen.getByTestId('mock-bar-chart');
    expect(chartElement.textContent).toContain('Unknown');
  });
});
