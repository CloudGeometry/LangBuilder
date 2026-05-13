import { act, renderHook } from "@testing-library/react";
import { useDebounce } from "../useDebounce";

describe("useDebounce", () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("returns initial value immediately", () => {
    const { result } = renderHook(() => useDebounce("initial", 500));
    expect(result.current).toBe("initial");
  });

  it("does not update value before delay", () => {
    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      { initialProps: { value: "initial", delay: 500 } },
    );

    rerender({ value: "updated", delay: 500 });

    // Before timer fires
    expect(result.current).toBe("initial");
  });

  it("updates value after delay", () => {
    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      { initialProps: { value: "initial", delay: 500 } },
    );

    rerender({ value: "updated", delay: 500 });

    act(() => {
      jest.advanceTimersByTime(500);
    });

    expect(result.current).toBe("updated");
  });

  it("cancels previous timer when value changes rapidly", () => {
    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      { initialProps: { value: "first", delay: 500 } },
    );

    rerender({ value: "second", delay: 500 });

    act(() => {
      jest.advanceTimersByTime(200);
    });

    rerender({ value: "third", delay: 500 });

    act(() => {
      jest.advanceTimersByTime(300);
    });

    // 200 + 300 = 500ms but the timer reset, so still not fired
    expect(result.current).toBe("first");

    act(() => {
      jest.advanceTimersByTime(200);
    });

    // 300 + 200 = 500ms after last change
    expect(result.current).toBe("third");
  });

  it("works with object values", () => {
    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      {
        initialProps: {
          value: { from: null, to: null } as { from: string | null; to: string | null },
          delay: 500,
        },
      },
    );

    const newValue = { from: "2025-01-01", to: "2025-12-31" };
    rerender({ value: newValue, delay: 500 });

    act(() => {
      jest.advanceTimersByTime(500);
    });

    expect(result.current).toEqual(newValue);
  });
});
