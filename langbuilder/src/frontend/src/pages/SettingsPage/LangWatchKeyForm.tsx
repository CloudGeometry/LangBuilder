import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { saveLangWatchKey } from "@/services/LangWatchService";
import { useGetKeyStatus } from "@/pages/UsagePage/hooks/useGetKeyStatus";

export function LangWatchKeyForm() {
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const queryClient = useQueryClient();

  const { data: keyStatus } = useGetKeyStatus();

  const saveMutation = useMutation({
    mutationFn: (key: string) => saveLangWatchKey(key),
    onSuccess: () => {
      setApiKey("");
      // Invalidate key status and usage summary cache
      queryClient.invalidateQueries({ queryKey: ["usage", "key-status"] });
      queryClient.invalidateQueries({ queryKey: ["usage", "summary"] });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey.trim()) return;
    saveMutation.mutate(apiKey.trim());
  };

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold">LangWatch API Key</h3>
        <p className="text-sm text-muted-foreground mt-1">
          Required to display AI cost and usage data in the Usage dashboard.
          Find your API key at{" "}
          <a
            href="https://app.langwatch.ai"
            target="_blank"
            rel="noopener noreferrer"
            className="underline"
          >
            app.langwatch.ai
          </a>
          .
        </p>
      </div>

      {/* Current key status */}
      {keyStatus?.has_key && (
        <Alert variant="default" className="border-green-200 bg-green-50">
          <CheckCircle2 className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-800">
            API key configured: <code>{keyStatus.key_preview}</code>
            {keyStatus.configured_at && (
              <span className="ml-2 text-xs text-green-600">
                (updated {new Date(keyStatus.configured_at).toLocaleDateString()})
              </span>
            )}
          </AlertDescription>
        </Alert>
      )}

      {/* Input form */}
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="space-y-1">
          <Label htmlFor="langwatch-api-key">
            {keyStatus?.has_key ? "Replace API Key" : "API Key"}
          </Label>
          <div className="flex gap-2">
            <Input
              id="langwatch-api-key"
              type={showKey ? "text" : "password"}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="lw_live_..."
              disabled={saveMutation.isPending}
              className="font-mono"
            />
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setShowKey(!showKey)}
            >
              {showKey ? "Hide" : "Show"}
            </Button>
          </div>
        </div>

        <Button
          type="submit"
          disabled={!apiKey.trim() || saveMutation.isPending}
        >
          {saveMutation.isPending && (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          )}
          {saveMutation.isPending ? "Validating..." : "Save & Validate"}
        </Button>
      </form>

      {/* Success state */}
      {saveMutation.isSuccess && (
        <Alert variant="default" className="border-green-200 bg-green-50">
          <CheckCircle2 className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-800">
            {saveMutation.data?.message}
          </AlertDescription>
        </Alert>
      )}

      {/* Error state */}
      {saveMutation.isError && (
        <Alert variant="destructive">
          <XCircle className="h-4 w-4" />
          <AlertDescription>
            {getErrorMessage(saveMutation.error)}
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}

function getErrorMessage(error: unknown): string {
  // Handle new Error instance shape (from updated LangWatchService)
  if (error instanceof Error) {
    const code = (error as any).code;
    if (code === "INVALID_KEY") {
      return "Invalid API key. Please check your LangWatch account settings and try again.";
    }
    if (code === "INSUFFICIENT_CREDITS") {
      return "Your LangWatch account has insufficient credits. Please upgrade your plan at langwatch.ai.";
    }
    if (code === "LANGWATCH_UNAVAILABLE") {
      return "Unable to reach LangWatch to validate your key. Please check your connection and try again.";
    }
    return error.message;
  }
  // Handle legacy plain-object shape (backward compatibility)
  if (error && typeof error === "object" && "detail" in error) {
    const detail = (error as { detail: { code?: string; message?: string } })
      .detail;
    if (detail?.code === "INVALID_KEY") {
      return "Invalid API key. Please check your LangWatch account settings and try again.";
    }
    if (detail?.code === "INSUFFICIENT_CREDITS") {
      return "Your LangWatch account has insufficient credits. Please upgrade your plan at langwatch.ai.";
    }
    if (detail?.code === "LANGWATCH_UNAVAILABLE") {
      return "Unable to reach LangWatch to validate your key. Please check your connection and try again.";
    }
    if (detail?.message) return detail.message;
  }
  return "An unexpected error occurred. Please try again.";
}
