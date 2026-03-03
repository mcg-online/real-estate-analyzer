import React from 'react';

const InvestmentMetrics = ({ analysis }) => {
  if (!analysis) {
    return <div className="text-gray-500">No analysis data available.</div>;
  }

  return (
    <div className="space-y-6">
      {/* Income & Expenses */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-blue-50 rounded-lg p-4 text-center">
          <p className="text-sm text-blue-600 font-medium">Monthly Rent</p>
          <p className="text-2xl font-bold text-blue-800">${analysis.monthly_rent?.toLocaleString()}</p>
        </div>
        <div className="bg-red-50 rounded-lg p-4 text-center">
          <p className="text-sm text-red-600 font-medium">Monthly Expenses</p>
          <p className="text-2xl font-bold text-red-800">${analysis.monthly_expenses?.total?.toLocaleString()}</p>
        </div>
        <div className={`rounded-lg p-4 text-center ${analysis.monthly_cash_flow >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
          <p className={`text-sm font-medium ${analysis.monthly_cash_flow >= 0 ? 'text-green-600' : 'text-red-600'}`}>Monthly Cash Flow</p>
          <p className={`text-2xl font-bold ${analysis.monthly_cash_flow >= 0 ? 'text-green-800' : 'text-red-800'}`}>
            ${analysis.monthly_cash_flow?.toLocaleString()}
          </p>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="bg-white border rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Key Investment Metrics</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <p className="text-sm text-gray-500">Cap Rate</p>
            <p className="text-xl font-bold text-gray-900">{analysis.cap_rate}%</p>
          </div>
          <div className="text-center">
            <p className="text-sm text-gray-500">Cash-on-Cash</p>
            <p className="text-xl font-bold text-gray-900">{analysis.cash_on_cash_return}%</p>
          </div>
          <div className="text-center">
            <p className="text-sm text-gray-500">Gross Yield</p>
            <p className="text-xl font-bold text-gray-900">{analysis.gross_yield}%</p>
          </div>
          <div className="text-center">
            <p className="text-sm text-gray-500">Break-even</p>
            <p className="text-xl font-bold text-gray-900">{analysis.break_even_point} yrs</p>
          </div>
        </div>
      </div>

      {/* ROI Details */}
      {analysis.roi && (
        <div className="bg-white border rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Return on Investment (5-Year)</h3>
          <dl className="space-y-2">
            <div className="flex justify-between">
              <dt className="text-gray-500">Total ROI</dt>
              <dd className="font-medium">{analysis.roi.total_roi}%</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Annualized ROI</dt>
              <dd className="font-medium">{analysis.roi.annualized_roi}%</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Projected Future Value</dt>
              <dd className="font-medium">${analysis.roi.future_value?.toLocaleString()}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Total Cash Flow (5yr)</dt>
              <dd className="font-medium">${analysis.roi.total_cash_flow?.toLocaleString()}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Appreciation Profit</dt>
              <dd className="font-medium">${analysis.roi.appreciation_profit?.toLocaleString()}</dd>
            </div>
          </dl>
        </div>
      )}

      {/* Expense Breakdown */}
      {analysis.monthly_expenses && (
        <div className="bg-white border rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Monthly Expense Breakdown</h3>
          <dl className="space-y-2">
            <div className="flex justify-between">
              <dt className="text-gray-500">Mortgage Payment</dt>
              <dd className="font-medium">${analysis.mortgage_payment?.toLocaleString()}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Property Tax</dt>
              <dd className="font-medium">${analysis.monthly_expenses.property_tax?.toLocaleString()}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Insurance</dt>
              <dd className="font-medium">${analysis.monthly_expenses.insurance?.toLocaleString()}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Maintenance</dt>
              <dd className="font-medium">${analysis.monthly_expenses.maintenance?.toLocaleString()}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Vacancy Cost</dt>
              <dd className="font-medium">${analysis.monthly_expenses.vacancy?.toLocaleString()}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Management</dt>
              <dd className="font-medium">${analysis.monthly_expenses.management?.toLocaleString()}</dd>
            </div>
            {analysis.monthly_expenses.hoa > 0 && (
              <div className="flex justify-between">
                <dt className="text-gray-500">HOA</dt>
                <dd className="font-medium">${analysis.monthly_expenses.hoa?.toLocaleString()}</dd>
              </div>
            )}
          </dl>
        </div>
      )}
    </div>
  );
};

export default InvestmentMetrics;
