import React from 'react';
import { render, screen } from '@testing-library/react';
import InvestmentSummary from '../InvestmentSummary';

const sampleProperties = [
  {
    _id: '1',
    price: 300000,
    score: 80,
    metrics: {
      cap_rate: 6.5,
      monthly_cash_flow: 400,
      roi: { annualized_roi: 12.5 },
    },
  },
  {
    _id: '2',
    price: 200000,
    score: 70,
    metrics: {
      cap_rate: 7.5,
      monthly_cash_flow: 600,
      roi: { annualized_roi: 14.0 },
    },
  },
];

describe('InvestmentSummary', () => {
  it('renders empty state when no properties are provided', () => {
    render(<InvestmentSummary properties={[]} />);
    expect(screen.getByText('No properties to summarize.')).toBeInTheDocument();
  });

  it('renders empty state when properties is null', () => {
    render(<InvestmentSummary properties={null} />);
    expect(screen.getByText('No properties to summarize.')).toBeInTheDocument();
  });

  it('renders total properties count', () => {
    render(<InvestmentSummary properties={sampleProperties} />);
    expect(screen.getByText('Total Properties')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('renders total portfolio value as currency', () => {
    render(<InvestmentSummary properties={sampleProperties} />);
    expect(screen.getByText('Total Portfolio Value')).toBeInTheDocument();
    expect(screen.getByText('$500,000')).toBeInTheDocument();
  });

  it('renders average property price as currency', () => {
    render(<InvestmentSummary properties={sampleProperties} />);
    expect(screen.getByText('Avg. Property Price')).toBeInTheDocument();
    expect(screen.getByText('$250,000')).toBeInTheDocument();
  });

  it('renders average cap rate as percentage', () => {
    render(<InvestmentSummary properties={sampleProperties} />);
    expect(screen.getByText('Avg. Cap Rate')).toBeInTheDocument();
    expect(screen.getByText('7.00%')).toBeInTheDocument();
  });

  it('renders average monthly cash flow', () => {
    render(<InvestmentSummary properties={sampleProperties} />);
    expect(screen.getByText('Avg. Monthly Cash Flow')).toBeInTheDocument();
    expect(screen.getByText('$500')).toBeInTheDocument();
  });

  it('renders average annualized ROI', () => {
    render(<InvestmentSummary properties={sampleProperties} />);
    expect(screen.getByText('Avg. Annualized ROI')).toBeInTheDocument();
    expect(screen.getByText('13.25%')).toBeInTheDocument();
  });

  it('renders average investment score', () => {
    render(<InvestmentSummary properties={sampleProperties} />);
    expect(screen.getByText('Avg. Investment Score')).toBeInTheDocument();
    expect(screen.getByText('75')).toBeInTheDocument();
  });

  it('handles properties without metrics gracefully', () => {
    const propertiesNoMetrics = [
      { _id: '1', price: 100000 },
      { _id: '2', price: 200000 },
    ];
    render(<InvestmentSummary properties={propertiesNoMetrics} />);
    expect(screen.getByText('$150,000')).toBeInTheDocument(); // avg price
    // Both cap rate and ROI are 0.00% when no metrics
    const zeroPercents = screen.getAllByText('0.00%');
    expect(zeroPercents.length).toBe(2);
  });

  it('renders all seven stat labels', () => {
    render(<InvestmentSummary properties={sampleProperties} />);
    expect(screen.getByText('Total Properties')).toBeInTheDocument();
    expect(screen.getByText('Total Portfolio Value')).toBeInTheDocument();
    expect(screen.getByText('Avg. Property Price')).toBeInTheDocument();
    expect(screen.getByText('Avg. Cap Rate')).toBeInTheDocument();
    expect(screen.getByText('Avg. Monthly Cash Flow')).toBeInTheDocument();
    expect(screen.getByText('Avg. Annualized ROI')).toBeInTheDocument();
    expect(screen.getByText('Avg. Investment Score')).toBeInTheDocument();
  });
});
