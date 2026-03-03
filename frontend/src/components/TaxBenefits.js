import React from 'react';

const TaxBenefits = ({ taxBenefits }) => {
  if (!taxBenefits) {
    return <div className="text-gray-500">Loading tax benefits...</div>;
  }

  const { depreciation, mortgage_interest_deduction, property_tax_deduction,
          local_tax_incentives, total_deductions, estimated_tax_savings, monthly_tax_savings } = taxBenefits;

  return (
    <div className="space-y-6">
      {/* Tax Savings Summary */}
      <div className="bg-green-50 border border-green-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-green-800 mb-2">Estimated Annual Tax Savings</h3>
        <p className="text-3xl font-bold text-green-600">${estimated_tax_savings?.toLocaleString()}</p>
        <p className="text-sm text-green-700 mt-1">${monthly_tax_savings?.toLocaleString()} / month</p>
      </div>

      {/* Depreciation */}
      <div className="bg-white border rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-3">Depreciation</h3>
        <dl className="space-y-2">
          <div className="flex justify-between">
            <dt className="text-gray-500">Building Value</dt>
            <dd className="font-medium">${depreciation?.building_value?.toLocaleString()}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-500">Land Value</dt>
            <dd className="font-medium">${depreciation?.land_value?.toLocaleString()}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-500">Annual Depreciation</dt>
            <dd className="font-medium text-green-600">${depreciation?.annual_depreciation?.toLocaleString()}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-500">Monthly Depreciation</dt>
            <dd className="font-medium">${depreciation?.monthly_depreciation?.toLocaleString()}</dd>
          </div>
        </dl>
      </div>

      {/* Other Deductions */}
      <div className="bg-white border rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-3">Other Deductions</h3>
        <dl className="space-y-2">
          <div className="flex justify-between">
            <dt className="text-gray-500">Mortgage Interest (Year 1)</dt>
            <dd className="font-medium">${mortgage_interest_deduction?.toLocaleString()}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-500">Property Tax</dt>
            <dd className="font-medium">${property_tax_deduction?.toLocaleString()}</dd>
          </div>
          <div className="flex justify-between border-t pt-2 mt-2">
            <dt className="text-gray-700 font-semibold">Total Deductions</dt>
            <dd className="font-bold text-green-600">${total_deductions?.toLocaleString()}</dd>
          </div>
        </dl>
      </div>

      {/* Local Tax Incentives */}
      {local_tax_incentives && (
        <div className="bg-white border rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-3">Local Tax Incentives</h3>
          <div className="space-y-2">
            <div className="flex items-center">
              <span className={`w-3 h-3 rounded-full mr-2 ${local_tax_incentives.has_opportunity_zone ? 'bg-green-500' : 'bg-gray-300'}`}></span>
              <span className="text-gray-600">Opportunity Zone</span>
            </div>
            <div className="flex items-center">
              <span className={`w-3 h-3 rounded-full mr-2 ${local_tax_incentives.has_historic_tax_credits ? 'bg-green-500' : 'bg-gray-300'}`}></span>
              <span className="text-gray-600">Historic Tax Credits</span>
            </div>
            <div className="flex items-center">
              <span className={`w-3 h-3 rounded-full mr-2 ${local_tax_incentives.has_homestead_exemption ? 'bg-green-500' : 'bg-gray-300'}`}></span>
              <span className="text-gray-600">Homestead Exemption</span>
            </div>
            <div className="flex items-center">
              <span className={`w-3 h-3 rounded-full mr-2 ${local_tax_incentives.has_renovation_incentives ? 'bg-green-500' : 'bg-gray-300'}`}></span>
              <span className="text-gray-600">Renovation Incentives</span>
            </div>
          </div>
          {local_tax_incentives.special_programs && local_tax_incentives.special_programs.length > 0 && (
            <div className="mt-3">
              <p className="text-sm font-medium text-gray-700">Special Programs:</p>
              <ul className="list-disc list-inside text-sm text-gray-600 mt-1">
                {local_tax_incentives.special_programs.map((program, index) => (
                  <li key={index}>{program}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default TaxBenefits;
