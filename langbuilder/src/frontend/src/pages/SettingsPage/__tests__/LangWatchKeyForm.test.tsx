import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";
import { LangWatchKeyForm } from "../LangWatchKeyForm";

// Mock the useGetKeyStatus hook
const mockUseGetKeyStatus = jest.fn();
jest.mock("@/pages/UsagePage/hooks/useGetKeyStatus", () => ({
  useGetKeyStatus: () => mockUseGetKeyStatus(),
}));

// Mock the saveLangWatchKey service
const mockSaveLangWatchKey = jest.fn();
jest.mock("@/services/LangWatchService", () => ({
  saveLangWatchKey: (...args: unknown[]) => mockSaveLangWatchKey(...args),
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe("LangWatchKeyForm", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Default: no key configured
    mockUseGetKeyStatus.mockReturnValue({ data: { has_key: false }, isLoading: false });
  });

  it("renders form with empty state when no key configured", () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <LangWatchKeyForm />
      </Wrapper>,
    );

    expect(screen.getByText("LangWatch API Key")).toBeInTheDocument();
    expect(screen.getByLabelText("API Key")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("lw_live_...")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Save & Validate/i })).toBeInTheDocument();
  });

  it("renders key status when key exists", () => {
    mockUseGetKeyStatus.mockReturnValue({
      data: {
        has_key: true,
        key_preview: "lw_live_***abc",
        configured_at: "2026-01-15T10:00:00Z",
      },
      isLoading: false,
    });

    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <LangWatchKeyForm />
      </Wrapper>,
    );

    expect(screen.getByText(/API key configured/i)).toBeInTheDocument();
    expect(screen.getByText("lw_live_***abc")).toBeInTheDocument();
    expect(screen.getByLabelText("Replace API Key")).toBeInTheDocument();
  });

  it("submit button is disabled when input is empty", () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <LangWatchKeyForm />
      </Wrapper>,
    );

    const submitButton = screen.getByRole("button", { name: /Save & Validate/i });
    expect(submitButton).toBeDisabled();
  });

  it("shows success alert after successful save", async () => {
    mockSaveLangWatchKey.mockResolvedValue({
      success: true,
      key_preview: "lw_live_***xyz",
      message: "API key validated and saved successfully.",
    });

    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <LangWatchKeyForm />
      </Wrapper>,
    );

    const input = screen.getByPlaceholderText("lw_live_...");
    fireEvent.change(input, { target: { value: "lw_live_testkey123" } });

    const submitButton = screen.getByRole("button", { name: /Save & Validate/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText("API key validated and saved successfully.")).toBeInTheDocument();
    });
  });

  it("maps INVALID_KEY error to user-friendly message", async () => {
    mockSaveLangWatchKey.mockRejectedValue({
      detail: { code: "INVALID_KEY", message: "Key is invalid" },
    });

    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <LangWatchKeyForm />
      </Wrapper>,
    );

    const input = screen.getByPlaceholderText("lw_live_...");
    fireEvent.change(input, { target: { value: "invalid_key" } });

    const submitButton = screen.getByRole("button", { name: /Save & Validate/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(
        screen.getByText(
          "Invalid API key. Please check your LangWatch account settings and try again.",
        ),
      ).toBeInTheDocument();
    });
  });

  it("clears input on successful save", async () => {
    mockSaveLangWatchKey.mockResolvedValue({
      success: true,
      key_preview: "lw_live_***xyz",
      message: "API key validated and saved successfully.",
    });

    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <LangWatchKeyForm />
      </Wrapper>,
    );

    const input = screen.getByPlaceholderText("lw_live_...");
    fireEvent.change(input, { target: { value: "lw_live_testkey123" } });
    expect(input).toHaveValue("lw_live_testkey123");

    const submitButton = screen.getByRole("button", { name: /Save & Validate/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(input).toHaveValue("");
    });
  });
});
