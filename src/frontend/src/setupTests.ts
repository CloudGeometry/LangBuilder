// Jest setup file for testing environment
import "@testing-library/jest-dom";

// Mock darkStore to avoid import.meta.env issues in Jest
jest.mock("./stores/darkStore", () => ({
  __esModule: true,
  default: jest.fn(() => ({
    isDark: false,
    setDark: jest.fn(),
    theme: "light",
    version: "1.0.0",
    stars: 0,
    refreshVersion: jest.fn(),
    refreshStars: jest.fn(),
    lastUpdated: new Date(),
  })),
  useDarkStore: jest.fn(() => ({
    isDark: false,
    setDark: jest.fn(),
    theme: "light",
    version: "1.0.0",
    stars: 0,
    refreshVersion: jest.fn(),
    refreshStars: jest.fn(),
    lastUpdated: new Date(),
  })),
}));

// Mock ResizeObserver if not available in test environment
global.ResizeObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Mock IntersectionObserver if not available in test environment
global.IntersectionObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Mock window.matchMedia for components that use it
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: jest.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Suppress console.error and console.warn in tests unless explicitly needed
const originalError = console.error;
const originalWarn = console.warn;

beforeAll(() => {
  console.error = (...args) => {
    if (
      typeof args[0] === "string" &&
      args[0].includes("Warning: ReactDOM.render is deprecated")
    ) {
      return;
    }
    originalError.call(console, ...args);
  };

  console.warn = (...args) => {
    if (
      typeof args[0] === "string" &&
      args[0].includes("componentWillReceiveProps has been renamed")
    ) {
      return;
    }
    originalWarn.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
  console.warn = originalWarn;
});
