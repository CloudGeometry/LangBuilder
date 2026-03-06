import type { Dispatch, SetStateAction } from "react";
import { usePatchUpdateFlow } from "@/controllers/API/queries/flows/use-patch-update-flow";
import useFlowStore from "@/stores/flowStore";
import PublishDropdown from "./deploy-dropdown";
import LockFlowButton from "./lock-flow-button";
import PlaygroundButton from "./playground-button";

type FlowToolbarOptionsProps = {
  open: boolean;
  setOpen: Dispatch<SetStateAction<boolean>>;
  openApiModal: boolean;
  setOpenApiModal: Dispatch<SetStateAction<boolean>>;
};
const FlowToolbarOptions = ({
  open,
  setOpen,
  openApiModal,
  setOpenApiModal,
}: FlowToolbarOptionsProps) => {
  const hasIO = useFlowStore((state) => state.hasIO);
  const currentFlow = useFlowStore((state) => state.currentFlow);
  const isLocked = currentFlow?.locked ?? false;
  const { mutate: patchUpdateFlow } = usePatchUpdateFlow();

  const handleToggleLock = () => {
    if (!currentFlow?.id) return;
    patchUpdateFlow({ id: currentFlow.id, locked: !isLocked });
  };

  return (
    <div className="flex items-center gap-1.5">
      <LockFlowButton isLocked={isLocked} onToggle={handleToggleLock} />
      <div className="flex h-full w-full gap-1.5 rounded-sm transition-all">
        <PlaygroundButton
          hasIO={hasIO}
          open={open}
          setOpen={setOpen}
          canvasOpen
        />
      </div>
      <PublishDropdown
        openApiModal={openApiModal}
        setOpenApiModal={setOpenApiModal}
      />
    </div>
  );
};

export default FlowToolbarOptions;
