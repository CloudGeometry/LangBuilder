import { useGetKeyStatus } from "../useGetKeyStatus";

// Mock the service
jest.mock("@/services/LangWatchService", () => ({
  getKeyStatus: jest.fn(),
}));

// Mock @tanstack/react-query
const mockUseQuery = jest.fn();
jest.mock("@tanstack/react-query", () => ({
  useQuery: (options: unknown) => mockUseQuery(options),
}));

describe("useGetKeyStatus", () => {
  beforeEach(() => {
    mockUseQuery.mockReset();
    mockUseQuery.mockReturnValue({ data: undefined, isLoading: false });
  });

  it("calls useQuery with correct queryKey", () => {
    useGetKeyStatus();

    const options = mockUseQuery.mock.calls[0][0];
    expect(options.queryKey).toEqual(["usage", "key-status"]);
  });

  it("configures staleTime to 5 minutes", () => {
    useGetKeyStatus();

    const options = mockUseQuery.mock.calls[0][0];
    expect(options.staleTime).toBe(5 * 60 * 1000);
  });

  it("configures retry to 1", () => {
    useGetKeyStatus();

    const options = mockUseQuery.mock.calls[0][0];
    expect(options.retry).toBe(1);
  });

  it("uses getKeyStatus as queryFn", () => {
    const { getKeyStatus } = jest.requireMock("@/services/LangWatchService");
    useGetKeyStatus();

    const options = mockUseQuery.mock.calls[0][0];
    expect(options.queryFn).toBe(getKeyStatus);
  });
});
