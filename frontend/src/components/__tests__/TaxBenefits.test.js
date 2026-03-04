import React from 'react';
import { render, screen } from '@testing-library/react';
import TaxBenefits from '../TaxBenefits';

const mockTaxBenefits = {
  depreciation: {
    building_value: 280000,
    land_value: 70000,
    annual_depreciation: 10182,
    monthly_depreciation: 849,
  },
  mortgage_interest_deduction: 12600,
  property_tax_deduction: 2400,
  total_deductions: 25182,
  estimated_tax_savings: 5540,
  monthly_tax_savings: 462,
  local_tax_incentives: {
    has_opportunity_zone: true,
    has_historic_tax_credits: false,
    has_homestead_exemption: true,
    has_renovation_incentives: false,
    special_programs: ['Texas Property Tax Relief', 'Austin Green Building Program'],
  },
};

describe('TaxBenefits', () => {
  it('shows loading state when taxBenefits is null', () => {
    render(<TaxBenefits taxBenefits={null} />);
    expect(screen.getByText('Loading tax benefits...')).toBeInTheDocument();
  });

  it('renders estimated annual tax savings', () => {
    render(<TaxBenefits taxBenefits={mockTaxBenefits} />);
    expect(screen.getByText('Estimated Annual Tax Savings')).toBeInTheDocument();
    expect(screen.getByText('$5,540')).toBeInTheDocument();
    expect(screen.getByText('$462 / month')).toBeInTheDocument();
  });

  it('renders depreciation details', () => {
    render(<TaxBenefits taxBenefits={mockTaxBenefits} />);
    expect(screen.getByText('Depreciation')).toBeInTheDocument();
    expect(screen.getByText('Building Value')).toBeInTheDocument();
    expect(screen.getByText('$280,000')).toBeInTheDocument();
    expect(screen.getByText('Land Value')).toBeInTheDocument();
    expect(screen.getByText('$70,000')).toBeInTheDocument();
    expect(screen.getByText('Annual Depreciation')).toBeInTheDocument();
    expect(screen.getByText('$10,182')).toBeInTheDocument();
  });

  it('renders other deductions section', () => {
    render(<TaxBenefits taxBenefits={mockTaxBenefits} />);
    expect(screen.getByText('Other Deductions')).toBeInTheDocument();
    expect(screen.getByText('Mortgage Interest (Year 1)')).toBeInTheDocument();
    expect(screen.getByText('$12,600')).toBeInTheDocument();
    expect(screen.getByText('Total Deductions')).toBeInTheDocument();
    expect(screen.getByText('$25,182')).toBeInTheDocument();
  });

  it('renders local tax incentives', () => {
    render(<TaxBenefits taxBenefits={mockTaxBenefits} />);
    expect(screen.getByText('Local Tax Incentives')).toBeInTheDocument();
    expect(screen.getByText('Opportunity Zone')).toBeInTheDocument();
    expect(screen.getByText('Historic Tax Credits')).toBeInTheDocument();
    expect(screen.getByText('Homestead Exemption')).toBeInTheDocument();
    expect(screen.getByText('Renovation Incentives')).toBeInTheDocument();
  });

  it('renders special programs', () => {
    render(<TaxBenefits taxBenefits={mockTaxBenefits} />);
    expect(screen.getByText('Special Programs:')).toBeInTheDocument();
    expect(screen.getByText('Texas Property Tax Relief')).toBeInTheDocument();
    expect(screen.getByText('Austin Green Building Program')).toBeInTheDocument();
  });

  it('does not render local tax incentives section when absent', () => {
    const noIncentives = { ...mockTaxBenefits, local_tax_incentives: null };
    render(<TaxBenefits taxBenefits={noIncentives} />);
    expect(screen.queryByText('Local Tax Incentives')).not.toBeInTheDocument();
  });
});
