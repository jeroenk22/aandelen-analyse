import '@testing-library/jest-dom';

// jsdom mist ResizeObserver (gebruikt door recharts)
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};
