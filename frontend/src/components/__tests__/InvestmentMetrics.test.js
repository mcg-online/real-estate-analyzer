import React from 'react';
import { render, screen } from '@testing-library/react';
import InvestmentMetrics from '../InvestmentMetrics';

const mockAnalysis = {
  monthly_rent: 2200,
  monthly_expenses: {
    total: 1400,
    property_tax: 300,
    insurance: 150,
    maintenance: 200,
    vacancy: 130,
    management: 220,
    hoa: 0,
  },
  monthly_cash_flow: 800,
  cap_rate: 7.2,
  cash_on_cash_return: 8.5,
  gross_yield: 9.1,
  break_even_point: 12,
  mortgage_payment: 1500,
  roi: {
    total_roi: 45.0,
    annualized_roi: 7.7,
    future_value: 420000,
    total_cash_flow: 27000,
    appreciation_profit: 50000,
  },
};

describe('InvestmentMetrics', () => {
  it('shows empty state when analysis is null', () => {
    render(<InvestmentMetrics analysis={null} />);
    expect(screen.getByText('No analysis data available.')).toBeInTheDocument();
  });

  it('renders monthly rent, expenses, and cash flow', () => {
    render(<InvestmentMetrics analysis={mockAnalysis} />);
    expect(screen.getByText('Monthly Rent')).toBeInTheDocument();
    expect(screen.getByText('Monthly Expenses')).toBeInTheDocument();
    expect(screen.getByText('Monthly Cash Flow')).toBeInTheDocument();
  });

  it('renders key investment metrics section', () => {
    render(<InvestmentMetrics analysis={mockAnalysis} />);
    expect(screen.getByText('Key Investment Metrics')).toBeInTheDocument();
    expect(screen.getByText('Cap Rate')).toBeInTheDocument();
    expect(screen.getByText('7.2%')).toBeInTheDocument();
    expect(screen.getByText('Cash-on-Cash')).toBeInTheDocument();
    expect(screen.getByText('8.5%')).toBeInTheDocument();
    expect(screen.getByText('Gross Yield')).toBeInTheDocument();
    expect(screen.getByText('9.1%')).toBeInTheDocument();
    expect(screen.getByText('Break-even')).toBeInTheDocument();
    expect(screen.getByText('12 yrs')).toBeInTheDocument();
  });

  it('renders ROI details when available', () => {
    render(<InvestmentMetrics analysis={mockAnalysis} />);
    expect(screen.getByText('Return on Investment (5-Year)')).toBeInTheDocument();
    expect(screen.getByText('Total ROI')).toBeInTheDocument();
    expect(screen.getByText('45%')).toBeInTheDocument();
    expect(screen.getByText('Annualized ROI')).toBeInTheDocument();
    expect(screen.getByText('7.7%')).toBeInTheDocument();
  });

  it('renders expense breakdown', () => {
    render(<InvestmentMetrics analysis={mockAnalysis} />);
    expect(screen.getByText('Monthly Expense Breakdown')).toBeInTheDocument();
    expect(screen.getByText('Property Tax')).toBeInTheDocument();
    expect(screen.getByText('Insurance')).toBeInTheDocument();
    expect(screen.getByText('Maintenance')).toBeInTheDocument();
    expect(screen.getByText('Vacancy Cost')).toBeInTheDocument();
    expect(screen.getByText('Management')).toBeInTheDocument();
  });

  it('does not render HOA when it is zero', () => {
    render(<InvestmentMetrics analysis={mockAnalysis} />);
    expect(screen.queryByText('HOA')).not.toBeInTheDocument();
  });

  it('renders HOA when it is greater than zero', () => {
    const withHoa = {
      ...mockAnalysis,
      monthly_expenses: { ...mockAnalysis.monthly_expenses, hoa: 250 },
    };
    render(<InvestmentMetrics analysis={withHoa} />);
    expect(screen.getByText('HOA')).toBeInTheDocument();
  });
});
