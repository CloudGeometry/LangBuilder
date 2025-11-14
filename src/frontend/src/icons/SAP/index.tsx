import React, { forwardRef } from "react";
import SAPIcon from "./SAP";

export const SAP = forwardRef<
  SVGSVGElement,
  React.PropsWithChildren<{}>
>((props, ref) => {
  return <SAPIcon ref={ref} {...props} />;
});
