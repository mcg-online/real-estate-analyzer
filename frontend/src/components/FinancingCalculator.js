import React, { useState } from 'react';

const FinancingCalculator = ({ property, financingOptions, onParamChange, params, onAnalyze }) => {
  const [selectedOption, setSelectedOption] = useState(0);

  const handleParamChange = (e) => {
    const { name, value, type, checked } = e.target;
    let processedValue;
    if (type === 'checkbox') {
      processedValue = checked;
    } else if (name === 'down_payment_percentage' || name === 'interest_rate') {
      // Sliders display whole-number percentages; convert to decimal fraction
      processedValue = parseFloat(value) / 100;
    } else if (type === 'number') {
      processedValue = parseFloat(value);
    } else {
      processedValue = value;
    }
    onParamChange(name, processedValue);
  };

  if (!property || !financingOptions) {
    return <div className="p-4 text-gray-500">Loading financing options...</div>;
  }

  const options = financingOptions.options || [];
  const localPrograms = financingOptions.local_programs || [];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="space-y-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Loan Options</h3>

          <div className="flex border-b mb-4">
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
              </button>
            ))}
          </div>

          {options.length > 0 && selectedOption < options.length && (
            <div>
              <h4 className="font-medium mb-3">{options[selectedOption].type} Loan Details</h4>
              <dl className="space-y-2">
                <div className="flex justify-between">
                  <dt className="text-gray-600">Loan Amount</dt>
                  <dd className="font-medium">${options[selectedOption].loan_amount.toLocaleString()}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-600">Down Payment</dt>
                  <dd className="font-medium">${options[selectedOption].down_payment.toLocaleString()} ({options[selectedOption].down_payment_percentage}%)</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-600">Interest Rate</dt>
                  <dd className="font-medium">{options[selectedOption].interest_rate}%</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-600">Term</dt>
                  <dd className="font-medium">{options[selectedOption].term_years} years</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-600">Monthly Payment</dt>
                  <dd className="font-medium">${options[selectedOption].monthly_payment.toLocaleString()}</dd>
                </div>
                {options[selectedOption].monthly_pmi > 0 && (
                  <div className="flex justify-between">
                    <dt className="text-gray-600">Monthly PMI</dt>
                    <dd className="font-medium">${options[selectedOption].monthly_pmi.toLocaleString()}</dd>
                  </div>
                )}
                {options[selectedOption].monthly_mip > 0 && (
                  <div className="flex justify-between">
                    <dt className="text-gray-600">Monthly MIP</dt>
                    <dd className="font-medium">${options[selectedOption].monthly_mip.toLocaleString()}</dd>
                  </div>
                )}
                {options[selectedOption].upfront_mip > 0 && (
                  <div className="flex justify-between">
                    <dt className="text-gray-600">Upfront MIP</dt>
                    <dd className="font-medium">${options[selectedOption].upfront_mip.toLocaleString()}</dd>
                  </div>
                )}
                {options[selectedOption].funding_fee > 0 && (
                  <div className="flex justify-between">
                    <dt className="text-gray-600">VA Funding Fee</dt>
                    <dd className="font-medium">${options[selectedOption].funding_fee.toLocaleString()} ({options[selectedOption].funding_fee_percentage}%)</dd>
                  </div>
                )}
                <div className="flex justify-between border-t pt-2 mt-2">
                  <dt className="text-gray-900 font-semibold">Total Monthly Payment</dt>
                  <dd className="font-bold text-blue-600">${options[selectedOption].total_monthly_payment.toLocaleString()}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-600">Total Interest Paid</dt>
                  <dd className="font-medium">${options[selectedOption].total_interest.toLocaleString()}</dd>
                </div>
              </dl>
            </div>
          )}

          {localPrograms.length > 0 && (
            <div className="mt-6">
              <h4 className="font-medium mb-2">Local Financing Programs</h4>
              <ul className="space-y-1 text-sm text-gray-600">
                {localPrograms.map((program, index) => (
                  <li key={index}><span className="font-medium">{program.name}</span>: {program.description}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      <div className="space-y-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Customize Financing</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Down Payment Percentage</label>
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  name="down_payment_percentage"
                  min="0"
                  max="50"
                  value={(params.down_payment_percentage * 100).toFixed(0)}
                  onChange={handleParamChange}
                  className="flex-1"
                />
                <span className="text-sm font-medium w-12">{(params.down_payment_percentage * 100).toFixed(0)}%</span>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Interest Rate</label>
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  name="interest_rate"
                  min="2"
                  max="10"
                  step="0.125"
                  value={(params.interest_rate * 100).toFixed(3)}
                  onChange={handleParamChange}
                  className="flex-1"
                />
                <span className="text-sm font-medium w-16">{(params.interest_rate * 100).toFixed(3)}%</span>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Loan Term</label>
              <select name="term_years" value={params.term_years} onChange={handleParamChange} className="w-full border rounded px-3 py-2">
                <option value="15">15 Years</option>
                <option value="20">20 Years</option>
                <option value="30">30 Years</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Credit Score</label>
              <select name="credit_score" value={params.credit_score} onChange={handleParamChange} className="w-full border rounded px-3 py-2">
                <option value="630">620-639</option>
                <option value="650">640-659</option>
                <option value="670">660-679</option>
                <option value="690">680-699</option>
                <option value="710">700-719</option>
                <option value="730">720-739</option>
                <option value="750">740-759</option>
                <option value="770">760+</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <input type="checkbox" name="veteran" checked={params.veteran || false} onChange={handleParamChange} id="veteran-checkbox" />
              <label htmlFor="veteran-checkbox" className="text-sm font-medium text-gray-700">Eligible for VA Loan</label>
            </div>

            {params.veteran && (
              <div className="flex items-center gap-2 ml-6">
                <input type="checkbox" name="first_time_va" checked={params.first_time_va || false} onChange={handleParamChange} id="first-time-va" />
                <label htmlFor="first-time-va" className="text-sm text-gray-600">First-time use of VA benefit</label>
              </div>
            )}

            <button onClick={onAnalyze} className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 transition">
              Calculate Financing Options
            </button>
          </div>

          <div className="mt-6 bg-gray-50 rounded p-4">
            <h4 className="font-medium mb-3">Monthly Cost Summary</h4>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-gray-600">Monthly Rent Estimate</dt>
                <dd className="text-green-600">+${property.metrics?.monthly_rent || 0}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-600">Mortgage Payment</dt>
                <dd className="text-red-600">-${options[selectedOption]?.monthly_payment || 0}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-600">Insurance, Taxes, etc.</dt>
                <dd className="text-red-600">-${property.metrics?.monthly_expenses?.total || 0}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-600">Monthly Tax Savings</dt>
                <dd className="text-green-600">+${property.tax_benefits?.monthly_tax_savings || 0}</dd>
              </div>
              <div className="flex justify-between border-t pt-2 mt-2 font-semibold">
                <dt>Net Monthly Cash Flow</dt>
                <dd className={`${(property.metrics?.monthly_cash_flow || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  ${property.metrics?.monthly_cash_flow || 0}
                </dd>
              </div>
            </dl>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FinancingCalculator;
