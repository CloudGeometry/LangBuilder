import ForwardedIconComponent from "@/components/common/genericIconComponent";
import ShadTooltip from "@/components/common/shadTooltipComponent";

interface LockFlowButtonProps {
  isLocked: boolean;
  onToggle: () => void;
}

const LockFlowButton = ({ isLocked, onToggle }: LockFlowButtonProps) => {
  return (
    <ShadTooltip content={isLocked ? "Unlock flow" : "Lock flow"}>
      <button
        data-testid="lock-flow-btn"
        onClick={onToggle}
        className="playground-btn-flow-toolbar hover:bg-accent"
        aria-label={isLocked ? "Unlock flow" : "Lock flow"}
      >
        <ForwardedIconComponent
          name={isLocked ? "Lock" : "LockOpen"}
          className="h-4 w-4 transition-all"
          strokeWidth={1.5}
        />
      </button>
    </ShadTooltip>
  );
};

export default LockFlowButton;
