import React, { useState } from 'react';

const FinancingCalculator = ({ property, financingOptions, onParamChange, params, onAnalyze }) => {
  const [selectedOption, setSelectedOption] = useState(0);

  const handleParamChange = (e) => {
    const { name, value, type, checked } = e.target;
    // Convert to appropriate type
    const processedValue = type === 'checkbox' 
      ? checked 
      : type === 'number' 
        ? (name.includes('percentage') ? parseFloat(value) / 100 : parseFloat(value))
        : value;
        
    onParamChange(name, processedValue);
  };

  if (!property || !financingOptions) {
    return Loading financing options...;
  }

  const options = financingOptions.options || [];
  const localPrograms = financingOptions.local_programs || [];

  return (
    
      
        
          Loan Options
          
          {/* Financing Option Tabs */}
          
            {options.map((option, index) => (
              <button
                key={index}
                className={`px-4 py-2 font-medium text-sm focus:outline-none ${
                  selectedOption === index
                    ? 'text-blue-600 border-b-2 border-blue-600'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
                onClick={() => setSelectedOption(index)}
              >
                {option.type}
              
            ))}
          
          
          {/* Selected Option Details */}
          {options.length > 0 && (
            
              {options[selectedOption].type} Loan Details
              
                Loan Amount
                ${options[selectedOption].loan_amount.toLocaleString()}
                
                Down Payment
                ${options[selectedOption].down_payment.toLocaleString()} ({options[selectedOption].down_payment_percentage}%)
                
                Interest Rate
                {options[selectedOption].interest_rate}%
                
                Term
                {options[selectedOption].term_years} years
                
                Monthly Payment
                ${options[selectedOption].monthly_payment.toLocaleString()}
                
                {options[selectedOption].monthly_pmi > 0 && (
                  <>
                    Monthly PMI
                    ${options[selectedOption].monthly_pmi.toLocaleString()}
                  </>
                )}
                
                {options[selectedOption].monthly_mip > 0 && (
                  <>
                    Monthly MIP
                    ${options[selectedOption].monthly_mip.toLocaleString()}
                  </>
                )}
                
                {options[selectedOption].upfront_mip > 0 && (
                  <>
                    Upfront MIP
                    ${options[selectedOption].upfront_mip.toLocaleString()}
                  </>
                )}
                
                {options[selectedOption].funding_fee > 0 && (
                  <>
                    VA Funding Fee
                    ${options[selectedOption].funding_fee.toLocaleString()} ({options[selectedOption].funding_fee_percentage}%)
                  </>
                )}
                
                Total Monthly Payment
                ${options[selectedOption].total_monthly_payment.toLocaleString()}
                
                Total Interest Paid
                ${options[selectedOption].total_interest.toLocaleString()}
              
            
          )}
          
          {/* Local Financing Programs */}
          {localPrograms.length > 0 && (
            
              Local Financing Programs
              
                {localPrograms.map((program, index) => (
                  {program.name}: {program.description}
                ))}
              
            
          )}
        
        
        
          Customize Financing
          
            
              
                Down Payment Percentage
              
              
                
                {(params.down_payment_percentage * 100).toFixed(0)}%
              
            
            
            
              
                Interest Rate
              
              
                
                {(params.interest_rate * 100).toFixed(3)}%
              
            
            
            
              
                Loan Term
              
              
                15 Years
                20 Years
                30 Years
              
            
            
            
              
                Credit Score
              
              
                620-639
                640-659
                660-679
                680-699
                700-719
                720-739
                740-759
                760+
              
            
            
            
              
                
                Eligible for VA Loan
              
            
            
            {params.veteran && (
              
                
                  
                  First-time use of VA benefit
                
              
            )}
            
            
              Calculate Financing Options
            
          
          
          {/* Payment vs Investment Summary */}
          
            Monthly Cost Summary
            
              Monthly Rent Estimate
              +${property.metrics?.monthly_rent || 0}
              
              Mortgage Payment
              -${options[selectedOption]?.monthly_payment || 0}
              
              Insurance, Taxes, etc.
              -${property.metrics?.monthly_expenses?.total || 0}
              
              Monthly Tax Savings
              +${property.tax_benefits?.monthly_tax_savings || 0}
              
              
              
              Net Monthly Cash Flow
              = 0 ? 'text-green-600' : 'text-red-600'}`}>
                ${property.metrics?.monthly_cash_flow || 0}
              
            
          
        
      
    
  );
};

export default FinancingCalculator;