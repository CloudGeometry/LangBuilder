import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert";

const ERROR_MESSAGES: Record<string, string> = {
  LANGWATCH_TIMEOUT: "LangWatch took too long to respond. Try again.",
  LANGWATCH_UNAVAILABLE: "LangWatch is temporarily unavailable.",
  KEY_NOT_CONFIGURED: "LangWatch API key not configured.",
};

const DEFAULT_MESSAGE = "An unexpected error occurred.";

function getErrorCode(error: unknown): string | null {
  if (!error || typeof error !== "object") return null;
  // Handle new Error instance shape (error.code)
  if (error instanceof Error) {
    const code = (error as any).code;
    return typeof code === "string" ? code : null;
  }
  // Handle legacy plain-object shape (error.detail.code)
  const e = error as Record<string, unknown>;
  if (e.code && typeof e.code === "string") return e.code;
  if (e.detail && typeof e.detail === "object") {
    const detail = e.detail as Record<string, unknown>;
    if (typeof detail.code === "string") return detail.code;
  }
  return null;
}

function getErrorMessage(error: unknown): string {
  const code = getErrorCode(error);
  if (code && code in ERROR_MESSAGES) {
    return ERROR_MESSAGES[code];
  }
  return DEFAULT_MESSAGE;
}

interface ErrorStateProps {
  error: unknown;
  onRetry: () => void;
  retryable?: boolean;
}

export function ErrorState({
  error,
  onRetry,
  retryable = true,
}: ErrorStateProps) {
  const message = getErrorMessage(error);

  return (
    <div
      data-testid="error-state"
      className="flex flex-col items-center justify-center p-8 space-y-4"
    >
      <Alert variant="destructive" className="max-w-lg">
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>{message}</AlertDescription>
      </Alert>
      {retryable && (
        <button
          data-testid="retry-button"
          onClick={onRetry}
          className="px-4 py-2 text-sm font-medium border rounded hover:bg-muted/50 transition-colors"
        >
          Try Again
        </button>
      )}
    </div>
  );
}
