import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import FinancingCalculator from '../FinancingCalculator';

const mockProperty = {
  _id: 'prop1',
  price: 400000,
  metrics: {
    monthly_rent: 2500,
    monthly_cash_flow: 800,
    monthly_expenses: { total: 500 },
  },
  tax_benefits: { monthly_tax_savings: 150 },
};

const mockFinancingOptions = {
  options: [
    {
      type: 'Conventional',
      loan_amount: 320000,
      down_payment: 80000,
      down_payment_percentage: 20,
      interest_rate: 4.5,
      term_years: 30,
      monthly_payment: 1621,
      monthly_pmi: 0,
      monthly_mip: 0,
      upfront_mip: 0,
      funding_fee: 0,
      funding_fee_percentage: 0,
      total_monthly_payment: 1621,
      total_interest: 263560,
    },
    {
      type: 'FHA',
      loan_amount: 387000,
      down_payment: 14000,
      down_payment_percentage: 3.5,
      interest_rate: 4.0,
      term_years: 30,
      monthly_payment: 1847,
      monthly_pmi: 0,
      monthly_mip: 200,
      upfront_mip: 6795,
      funding_fee: 0,
      funding_fee_percentage: 0,
      total_monthly_payment: 2047,
      total_interest: 270920,
    },
  ],
  local_programs: [
    { name: 'Austin DPA', description: 'Down payment assistance up to $15,000' },
  ],
};

const defaultParams = {
  down_payment_percentage: 0.20,
  interest_rate: 0.045,
  term_years: 30,
  holding_period: 5,
  appreciation_rate: 0.03,
  tax_bracket: 0.22,
  credit_score: 720,
  veteran: false,
  first_time_va: true,
};

describe('FinancingCalculator', () => {
  it('renders loading state when property or financing options are missing', () => {
    render(
      <FinancingCalculator
        property={null}
        financingOptions={null}
        onParamChange={jest.fn()}
        params={defaultParams}
        onAnalyze={jest.fn()}
      />
    );
    expect(screen.getByText('Loading financing options...')).toBeInTheDocument();
  });

  it('renders loan option tabs', () => {
    render(
      <FinancingCalculator
        property={mockProperty}
        financingOptions={mockFinancingOptions}
        onParamChange={jest.fn()}
        params={defaultParams}
        onAnalyze={jest.fn()}
      />
    );
    expect(screen.getByText('Conventional')).toBeInTheDocument();
    expect(screen.getByText('FHA')).toBeInTheDocument();
  });

  it('shows Conventional loan details by default', () => {
    render(
      <FinancingCalculator
        property={mockProperty}
        financingOptions={mockFinancingOptions}
        onParamChange={jest.fn()}
        params={defaultParams}
        onAnalyze={jest.fn()}
      />
    );
    expect(screen.getByText('Conventional Loan Details')).toBeInTheDocument();
    expect(screen.getByText('$320,000')).toBeInTheDocument(); // loan amount
    expect(screen.getByText(/\$80,000/)).toBeInTheDocument(); // down payment
  });

  it('switches to FHA tab on click', () => {
    render(
      <FinancingCalculator
        property={mockProperty}
        financingOptions={mockFinancingOptions}
        onParamChange={jest.fn()}
        params={defaultParams}
        onAnalyze={jest.fn()}
      />
    );

    fireEvent.click(screen.getByText('FHA'));
    expect(screen.getByText('FHA Loan Details')).toBeInTheDocument();
    expect(screen.getByText('$387,000')).toBeInTheDocument(); // FHA loan amount
  });

  it('renders customize financing section with sliders', () => {
    render(
      <FinancingCalculator
        property={mockProperty}
        financingOptions={mockFinancingOptions}
        onParamChange={jest.fn()}
        params={defaultParams}
        onAnalyze={jest.fn()}
      />
    );
    expect(screen.getByText('Customize Financing')).toBeInTheDocument();
    expect(screen.getByText('Down Payment Percentage')).toBeInTheDocument();
    // "Interest Rate" appears in both loan details (dt) and customize section (label)
    expect(screen.getAllByText('Interest Rate').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Loan Term')).toBeInTheDocument();
    expect(screen.getByText('Credit Score')).toBeInTheDocument();
  });

  it('renders Calculate Financing Options button', () => {
    render(
      <FinancingCalculator
        property={mockProperty}
        financingOptions={mockFinancingOptions}
        onParamChange={jest.fn()}
        params={defaultParams}
        onAnalyze={jest.fn()}
      />
    );
    expect(screen.getByRole('button', { name: 'Calculate Financing Options' })).toBeInTheDocument();
  });

  it('calls onAnalyze when Calculate button is clicked', () => {
    const onAnalyze = jest.fn();
    render(
      <FinancingCalculator
        property={mockProperty}
        financingOptions={mockFinancingOptions}
        onParamChange={jest.fn()}
        params={defaultParams}
        onAnalyze={onAnalyze}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'Calculate Financing Options' }));
    expect(onAnalyze).toHaveBeenCalledTimes(1);
  });

  it('renders monthly cost summary', () => {
    render(
      <FinancingCalculator
        property={mockProperty}
        financingOptions={mockFinancingOptions}
        onParamChange={jest.fn()}
        params={defaultParams}
        onAnalyze={jest.fn()}
      />
    );
    expect(screen.getByText('Monthly Cost Summary')).toBeInTheDocument();
    expect(screen.getByText('Monthly Rent Estimate')).toBeInTheDocument();
    expect(screen.getByText('Mortgage Payment')).toBeInTheDocument();
    expect(screen.getByText('Net Monthly Cash Flow')).toBeInTheDocument();
  });

  it('renders local programs when available', () => {
    render(
      <FinancingCalculator
        property={mockProperty}
        financingOptions={mockFinancingOptions}
        onParamChange={jest.fn()}
        params={defaultParams}
        onAnalyze={jest.fn()}
      />
    );
    expect(screen.getByText('Local Financing Programs')).toBeInTheDocument();
    expect(screen.getByText(/Austin DPA/)).toBeInTheDocument();
    expect(screen.getByText(/Down payment assistance up to \$15,000/)).toBeInTheDocument();
  });

  it('shows VA loan checkbox', () => {
    render(
      <FinancingCalculator
        property={mockProperty}
        financingOptions={mockFinancingOptions}
        onParamChange={jest.fn()}
        params={defaultParams}
        onAnalyze={jest.fn()}
      />
    );
    expect(screen.getByLabelText('Eligible for VA Loan')).toBeInTheDocument();
  });

  it('shows first-time VA checkbox when veteran is checked', () => {
    const veteranParams = { ...defaultParams, veteran: true };
    render(
      <FinancingCalculator
        property={mockProperty}
        financingOptions={mockFinancingOptions}
        onParamChange={jest.fn()}
        params={veteranParams}
        onAnalyze={jest.fn()}
      />
    );
    expect(screen.getByLabelText('First-time use of VA benefit')).toBeInTheDocument();
  });

  it('does not show first-time VA checkbox when veteran is false', () => {
    render(
      <FinancingCalculator
        property={mockProperty}
        financingOptions={mockFinancingOptions}
        onParamChange={jest.fn()}
        params={defaultParams}
        onAnalyze={jest.fn()}
      />
    );
    expect(screen.queryByLabelText('First-time use of VA benefit')).not.toBeInTheDocument();
  });

  it('calls onParamChange directly for non-slider select inputs', () => {
    const onParamChange = jest.fn();
    render(
      <FinancingCalculator
        property={mockProperty}
        financingOptions={mockFinancingOptions}
        onParamChange={onParamChange}
        params={defaultParams}
        onAnalyze={jest.fn()}
      />
    );

    // Select elements have type 'select-one', so the handler falls through
    // to the else branch and passes the raw string value
    const termSelect = screen.getByDisplayValue('30 Years');
    fireEvent.change(termSelect, { target: { name: 'term_years', value: '15' } });
    expect(onParamChange).toHaveBeenCalledWith('term_years', '15');
  });

  it('debounces slider changes for down_payment_percentage', () => {
    jest.useFakeTimers();
    const onParamChange = jest.fn();

    render(
      <FinancingCalculator
        property={mockProperty}
        financingOptions={mockFinancingOptions}
        onParamChange={onParamChange}
        params={defaultParams}
        onAnalyze={jest.fn()}
      />
    );

    // The down payment slider (type=range with name=down_payment_percentage)
    const sliders = screen.getAllByRole('slider');
    const downPaymentSlider = sliders.find(s => s.getAttribute('name') === 'down_payment_percentage');

    // Fire change event
    fireEvent.change(downPaymentSlider, { target: { name: 'down_payment_percentage', value: '25' } });

    // Should NOT have been called yet (debounced)
    expect(onParamChange).not.toHaveBeenCalled();

    // Advance timers by 300ms (the debounce delay)
    act(() => {
      jest.advanceTimersByTime(300);
    });

    expect(onParamChange).toHaveBeenCalledWith('down_payment_percentage', 0.25);
    jest.useRealTimers();
  });
});
