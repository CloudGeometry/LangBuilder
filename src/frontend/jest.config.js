module.exports = {
  preset: "ts-jest",
  testEnvironment: "jsdom",
  injectGlobals: true,
  moduleNameMapper: {
    // Asset and style mocks must be before the @/ alias to avoid conflicts
    "\\.(css|less|scss|sass)$": "identity-obj-proxy",
    "\\.svg(\\?react)?$": "<rootDir>/src/__mocks__/svg.tsx",
    "\\.jsx$": "<rootDir>/src/__mocks__/svg.tsx",
    // Special mocks for problematic modules
    "^react-markdown$": "<rootDir>/src/__mocks__/react-markdown.tsx",
    "^lucide-react/dynamicIconImports$":
      "<rootDir>/src/__mocks__/lucide-react.ts",
    "^@jsonquerylang/jsonquery$": "<rootDir>/src/__mocks__/jsonquery.ts",
    "^vanilla-jsoneditor$": "<rootDir>/src/__mocks__/vanilla-jsoneditor.ts",
    // Path alias (must be last to not interfere with other patterns)
    "^@/(.*)$": "<rootDir>/src/$1",
  },
  setupFilesAfterEnv: ["<rootDir>/src/setupTests.ts"],
  testMatch: [
    "<rootDir>/src/**/__tests__/**/*.{ts,tsx}",
    "<rootDir>/src/**/*.{test,spec}.{ts,tsx}",
  ],
  transform: {
    "^.+\\.(ts|tsx)$": [
      "ts-jest",
      {
        useESM: false,
      },
    ],
    "^.+\\.jsx$": [
      "ts-jest",
      {
        tsconfig: {
          jsx: "react",
          allowJs: true,
        },
      },
    ],
    // Transform ESM modules (like react-markdown) from node_modules
    "^.+\\.(js|mjs)$": [
      "ts-jest",
      {
        tsconfig: {
          allowJs: true,
          esModuleInterop: true,
          allowSyntheticDefaultImports: true,
        },
        useESM: false,
      },
    ],
  },
  moduleFileExtensions: ["ts", "tsx", "js", "jsx", "json"],
  // Ignore node_modules except for packages that need transformation
  transformIgnorePatterns: [
    "node_modules/(?!(.*\\.mjs$|@testing-library|@jsonquerylang|vanilla-jsoneditor|react-markdown|remark-.*|rehype-.*|unified|vfile.*|unist-.*|bail|is-plain-obj|trough|mdast-.*|micromark.*|decode-named-character-reference|character-entities|ccount|escape-string-regexp|markdown-table|property-information|space-separated-tokens|comma-separated-tokens|hast-util-.*|html-void-elements|web-namespaces|zwitch|trim-lines))",
  ],

  // Coverage configuration
  collectCoverage: true,
  collectCoverageFrom: [
    "src/**/*.{ts,tsx}",
    "!src/**/*.{test,spec}.{ts,tsx}",
    "!src/**/tests/**",
    "!src/**/__tests__/**",
    "!src/setupTests.ts",
    "!src/vite-env.d.ts",
    "!src/**/*.d.ts",
  ],
  coverageDirectory: "coverage",
  coverageReporters: ["text", "lcov", "html", "json-summary"],
  coveragePathIgnorePatterns: ["/node_modules/", "/tests/"],

  // CI-specific configuration
  ...(process.env.CI === "true" && {
    reporters: [
      "default",
      [
        "jest-junit",
        {
          outputDirectory: "test-results",
          outputName: "junit.xml",
          ancestorSeparator: " › ",
          uniqueOutputName: "false",
          suiteNameTemplate: "{filepath}",
          classNameTemplate: "{classname}",
          titleTemplate: "{title}",
        },
      ],
    ],
    maxWorkers: "50%",
    verbose: true,
  }),
};
