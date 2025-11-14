import React, { forwardRef } from "react";
import SvgJira from "./Jira";

export const Jira = forwardRef<
  SVGSVGElement,
  React.PropsWithChildren<{}>
>((props, ref) => {
  return <SvgJira ref={ref} {...props} />;
});
