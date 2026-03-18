import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
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

describe("LangWatchKeyForm - comprehensive tests", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseGetKeyStatus.mockReturnValue({
      data: { has_key: false },
      isLoading: false,
    });
  });

  it("test_show_hide_toggle_works — toggling show/hide changes input type", () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <LangWatchKeyForm />
      </Wrapper>,
    );

    const input = screen.getByPlaceholderText("lw_live_...");
    // Default: password type
    expect(input).toHaveAttribute("type", "password");

    const showButton = screen.getByRole("button", { name: /Show/i });
    fireEvent.click(showButton);

    // After clicking Show: text type
    expect(input).toHaveAttribute("type", "text");

    const hideButton = screen.getByRole("button", { name: /Hide/i });
    fireEvent.click(hideButton);

    // After clicking Hide: password type again
    expect(input).toHaveAttribute("type", "password");
  });

  it("test_submit_calls_mutation — form submit triggers saveLangWatchKey", async () => {
    mockSaveLangWatchKey.mockResolvedValue({
      success: true,
      key_preview: "lw_live_***test",
      message: "Key saved.",
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
      expect(mockSaveLangWatchKey).toHaveBeenCalledWith("lw_live_testkey123");
    });
  });

  it("test_loading_state_shows_spinner — spinner visible during pending", async () => {
    // Make the mutation take a while to resolve
    let resolvePromise: (value: unknown) => void;
    const pendingPromise = new Promise((resolve) => {
      resolvePromise = resolve;
    });
    mockSaveLangWatchKey.mockReturnValue(pendingPromise);

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

    // While pending, the button shows "Validating..."
    await waitFor(() => {
      expect(screen.getByText("Validating...")).toBeInTheDocument();
    });

    // Resolve to clean up
    act(() => {
      resolvePromise!({
        success: true,
        key_preview: "lw_live_***test",
        message: "Done.",
      });
    });
  });

  it("test_error_insufficient_credits_message — correct message for INSUFFICIENT_CREDITS", async () => {
    mockSaveLangWatchKey.mockRejectedValue({
      detail: {
        code: "INSUFFICIENT_CREDITS",
        message: "Not enough credits",
      },
    });

    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <LangWatchKeyForm />
      </Wrapper>,
    );

    const input = screen.getByPlaceholderText("lw_live_...");
    fireEvent.change(input, { target: { value: "lw_live_validkey" } });

    const submitButton = screen.getByRole("button", { name: /Save & Validate/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(
        screen.getByText(
          "Your LangWatch account has insufficient credits. Please upgrade your plan at langwatch.ai.",
        ),
      ).toBeInTheDocument();
    });
  });

  it("test_error_langwatch_unavailable_message — correct message for LANGWATCH_UNAVAILABLE", async () => {
    mockSaveLangWatchKey.mockRejectedValue({
      detail: {
        code: "LANGWATCH_UNAVAILABLE",
        message: "Service unreachable",
      },
    });

    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <LangWatchKeyForm />
      </Wrapper>,
    );

    const input = screen.getByPlaceholderText("lw_live_...");
    fireEvent.change(input, { target: { value: "lw_live_validkey" } });

    const submitButton = screen.getByRole("button", { name: /Save & Validate/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(
        screen.getByText(
          "Unable to reach LangWatch to validate your key. Please check your connection and try again.",
        ),
      ).toBeInTheDocument();
    });
  });

  it("test_api_key_cleared_after_success — input value cleared on success", async () => {
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
