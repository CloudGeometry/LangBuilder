import { useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import ShadTooltipComponent from "@/components/common/shadTooltipComponent";
import IconComponent from "@/components/common/genericIconComponent";
import { useGetPublishStatus } from "@/controllers/API/queries/flows/use-get-publish-status";
import useFlowsManagerStore from "@/stores/flowsManagerStore";

export default function PublishStatusBadge() {
  const currentFlow = useFlowsManagerStore((state) => state.currentFlow);
  const flowId = currentFlow?.id;

  const { data: publishRecords, refetch } = useGetPublishStatus(
    { flow_id: flowId ?? "" },
    {
      refetchInterval: 30000, // Refetch every 30 seconds
    },
  );

  const activePublications = publishRecords?.filter(
    (record) => record.status === "ACTIVE",
  );

  const hasActivePublications = activePublications && activePublications.length > 0;

  if (!hasActivePublications) {
    return null;
  }

  const openwebuiPublications = activePublications.filter(
    (record) => record.platform === "openwebui",
  );

  const tooltipContent = (
    <div className="space-y-1">
      <div className="font-semibold">Published to:</div>
      {openwebuiPublications.map((record, idx) => (
        <div key={idx} className="text-xs">
          <div>• OpenWebUI: {record.platform_url}</div>
          <div className="ml-3 text-muted-foreground">
            Model: {record.metadata?.model_name || record.external_id}
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <ShadTooltipComponent side="bottom" content={tooltipContent}>
      <Badge
        variant="outline"
        className="flex items-center gap-1 border-green-500 bg-green-50 text-green-700 hover:bg-green-100 dark:bg-green-950 dark:text-green-300"
      >
        <IconComponent name="Globe" className="h-3 w-3" />
        <span className="text-xs">Published ({openwebuiPublications.length})</span>
      </Badge>
    </ShadTooltipComponent>
  );
}
