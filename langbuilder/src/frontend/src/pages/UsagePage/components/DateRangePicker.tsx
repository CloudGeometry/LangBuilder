import { useCallback, useState } from "react";
import { CalendarIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

interface DateRange {
  from: string | null; // ISO 8601: "YYYY-MM-DD"
  to: string | null;
}

interface DateRangePickerProps {
  value: DateRange;
  onChange: (range: DateRange) => void;
}

const PRESETS = [
  {
    label: "Last 24h",
    getDates: () => {
      const to = new Date();
      const from = new Date(to);
      from.setDate(from.getDate() - 1);
      return { from: toISODate(from), to: toISODate(to) };
    },
  },
  {
    label: "Last 7 days",
    getDates: () => {
      const to = new Date();
      const from = new Date(to);
      from.setDate(from.getDate() - 7);
      return { from: toISODate(from), to: toISODate(to) };
    },
  },
  {
    label: "Last 14 days",
    getDates: () => {
      const to = new Date();
      const from = new Date(to);
      from.setDate(from.getDate() - 14);
      return { from: toISODate(from), to: toISODate(to) };
    },
  },
  {
    label: "Last 30 days",
    getDates: () => {
      const to = new Date();
      const from = new Date(to);
      from.setDate(from.getDate() - 30);
      return { from: toISODate(from), to: toISODate(to) };
    },
  },
];

function toISODate(date: Date): string {
  return date.toISOString().split("T")[0];
}

export function formatDisplayRange(
  from: string | null,
  to: string | null,
): string {
  if (!from && !to) return "All time";
  if (from && to) return `${from} \u2013 ${to}`;
  if (from) return `From ${from}`;
  return `Until ${to}`;
}

export function DateRangePicker({ value, onChange }: DateRangePickerProps) {
  const [open, setOpen] = useState(false);

  const handlePreset = useCallback(
    (preset: (typeof PRESETS)[0]) => {
      onChange(preset.getDates());
      setOpen(false);
    },
    [onChange],
  );

  const handleFromChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange({ ...value, from: e.target.value || null });
    },
    [value, onChange],
  );

  const handleToChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange({ ...value, to: e.target.value || null });
    },
    [value, onChange],
  );

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          className="w-[240px] justify-start text-left font-normal"
          data-testid="date-range-picker-trigger"
        >
          <CalendarIcon className="mr-2 h-4 w-4" />
          {formatDisplayRange(value.from, value.to)}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-4" align="start">
        {/* Preset shortcuts */}
        <div className="grid grid-cols-2 gap-2 mb-4">
          {PRESETS.map((preset) => (
            <Button
              key={preset.label}
              variant="outline"
              size="sm"
              onClick={() => handlePreset(preset)}
              data-testid={`preset-${preset.label.replace(/\s+/g, "-").toLowerCase()}`}
            >
              {preset.label}
            </Button>
          ))}
        </div>

        {/* Manual date inputs */}
        <div className="space-y-2">
          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium text-muted-foreground">
              From
            </label>
            <input
              type="date"
              value={value.from ?? ""}
              onChange={handleFromChange}
              max={value.to ?? undefined}
              className="rounded-md border border-input bg-background px-3 py-1 text-sm"
              data-testid="date-from-input"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium text-muted-foreground">
              To
            </label>
            <input
              type="date"
              value={value.to ?? ""}
              onChange={handleToChange}
              min={value.from ?? undefined}
              className="rounded-md border border-input bg-background px-3 py-1 text-sm"
              data-testid="date-to-input"
            />
          </div>
        </div>

        {/* Clear button */}
        {(value.from || value.to) && (
          <Button
            variant="ghost"
            size="sm"
            className="mt-3 w-full"
            data-testid="date-clear-button"
            onClick={() => {
              onChange({ from: null, to: null });
              setOpen(false);
            }}
          >
            Clear dates
          </Button>
        )}
      </PopoverContent>
    </Popover>
  );
}
