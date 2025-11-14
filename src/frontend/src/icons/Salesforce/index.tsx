import React, { forwardRef } from "react";
import SalesforceIcon from "./Salesforce";

export const Salesforce = forwardRef<
  SVGSVGElement,
  React.PropsWithChildren<{}>
>((props, ref) => {
  return <SalesforceIcon ref={ref} {...props} />;
});
