import React, { forwardRef } from "react";
import WorkdayIcon from "./Workday";

export const Workday = forwardRef<
  SVGSVGElement,
  React.PropsWithChildren<{}>
>((props, ref) => {
  return <WorkdayIcon ref={ref} {...props} />;
});
