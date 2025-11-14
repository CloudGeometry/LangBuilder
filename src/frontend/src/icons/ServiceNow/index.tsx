import React, { forwardRef } from "react";
import ServiceNowIcon from "./ServiceNow";

export const ServiceNow = forwardRef<
  SVGSVGElement,
  React.PropsWithChildren<{}>
>((props, ref) => {
  return <ServiceNowIcon ref={ref} {...props} />;
});
