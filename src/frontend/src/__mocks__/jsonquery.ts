// Mock for @jsonquerylang/jsonquery to avoid Jest module resolution issues
export const jsonquery = jest.fn();
export default { jsonquery };
