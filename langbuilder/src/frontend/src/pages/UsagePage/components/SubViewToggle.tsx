import { Button } from "@/components/ui/button";

interface SubViewToggleProps {
  value: "flows" | "mcp";
  onChange: (value: "flows" | "mcp") => void;
}

const tabs: { key: "flows" | "mcp"; label: string }[] = [
  { key: "mcp", label: "MCP Server" },
  { key: "flows", label: "Flows" },
];

export function SubViewToggle({ value, onChange }: SubViewToggleProps) {
  return (
    <div data-testid="sub-view-toggle" className="flex flex-row-reverse">
      <div className="w-full border-b dark:border-border" />
      {tabs.map(({ key, label }) => (
        <Button
          key={key}
          unstyled
          data-testid={`sub-view-${key}`}
          onClick={() => {
            if (key !== value) onChange(key);
          }}
          className={`border-b ${
            value === key
              ? "border-b-2 border-foreground text-foreground"
              : "border-border text-muted-foreground hover:text-foreground"
          } text-nowrap px-2 pb-2 pt-1 text-mmd`}
        >
          <div className={value === key ? "-mb-px" : ""}>{label}</div>
        </Button>
      ))}
    </div>
  );
}
