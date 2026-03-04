// jest-dom adds custom jest matchers for asserting on DOM nodes.
import '@testing-library/jest-dom';

// ---- Mock leaflet ----
jest.mock('leaflet', () => {
  const markerInstance = {
    addTo: jest.fn().mockReturnThis(),
    bindPopup: jest.fn().mockReturnThis(),
    remove: jest.fn(),
  };

  const mapInstance = {
    setView: jest.fn().mockReturnThis(),
    remove: jest.fn(),
    eachLayer: jest.fn(),
    removeLayer: jest.fn(),
    fitBounds: jest.fn(),
  };

  const tileLayerInstance = {
    addTo: jest.fn(),
  };

  const L = {
    map: jest.fn(() => mapInstance),
    tileLayer: jest.fn(() => tileLayerInstance),
    marker: jest.fn(() => markerInstance),
    divIcon: jest.fn((opts) => opts),
    Marker: class Marker {},
  };

  return L;
});

jest.mock('leaflet/dist/leaflet.css', () => {});

// ---- Mock chart.js ----
jest.mock('chart.js', () => ({
  Chart: { register: jest.fn() },
  CategoryScale: 'CategoryScale',
  LinearScale: 'LinearScale',
  BarElement: 'BarElement',
  Title: 'Title',
  Tooltip: 'Tooltip',
  Legend: 'Legend',
}));

// ---- Mock chartSetup (shared Chart.js registration module) ----
jest.mock('./chartSetup', () => {});

// ---- Mock react-chartjs-2 ----
jest.mock('react-chartjs-2', () => ({
  Bar: (props) => <div data-testid="mock-bar-chart">{JSON.stringify(props.data?.labels)}</div>,
  Line: (props) => <div data-testid="mock-line-chart" />,
  Pie: (props) => <div data-testid="mock-pie-chart" />,
}));

// ---- Mock services/api as a default mock that tests can override ----
jest.mock('./services/api', () => ({
  __esModule: true,
  default: {
    getProperties: jest.fn(),
    getProperty: jest.fn(),
    getPropertyAnalysis: jest.fn(),
    customizeAnalysis: jest.fn(),
    getTopMarkets: jest.fn(),
    login: jest.fn(),
    register: jest.fn(),
    logout: jest.fn(),
  },
}));
