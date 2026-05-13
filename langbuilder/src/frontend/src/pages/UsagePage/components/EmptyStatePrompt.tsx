interface EmptyStatePromptProps {
  variant: "no_key" | "no_data";
  isAdmin: boolean;
}

export function EmptyStatePrompt({ variant, isAdmin }: EmptyStatePromptProps) {
  if (variant === "no_key") {
    return (
      <div
        data-testid="empty-state-no-key"
        className="flex flex-col items-center justify-center p-12 text-center space-y-4"
      >
        <div className="rounded-full bg-muted p-4">
          <svg
            className="h-8 w-8 text-muted-foreground"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"
            />
          </svg>
        </div>
        <div className="space-y-2">
          <h2 className="text-lg font-semibold">
            LangWatch API key not configured
          </h2>
          {isAdmin ? (
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">
                Configure your LangWatch API key to start tracking usage and
                costs.
              </p>
              <a
                data-testid="admin-settings-link"
                href="/settings/langwatch"
                className="inline-flex items-center text-sm font-medium text-primary underline underline-offset-4 hover:no-underline"
              >
                Go to Admin Settings
              </a>
            </div>
          ) : (
            <p
              data-testid="non-admin-message"
              className="text-sm text-muted-foreground"
            >
              Please contact your administrator to configure the LangWatch API
              key.
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="empty-state-no-data"
      className="flex flex-col items-center justify-center p-12 text-center space-y-4"
    >
      <div className="rounded-full bg-muted p-4">
        <svg
          className="h-8 w-8 text-muted-foreground"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
          />
        </svg>
      </div>
      <div className="space-y-2">
        <h2 className="text-lg font-semibold">
          No usage data found for this period
        </h2>
        <p className="text-sm text-muted-foreground">
          Try to adjust the date range to see usage data from a different period.
        </p>
      </div>
    </div>
  );
}
