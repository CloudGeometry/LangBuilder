import React, { forwardRef } from "react";
import GoogleSheetsIcon from "./GoogleSheets";

export const GoogleSheets = forwardRef<
  SVGSVGElement,
  React.PropsWithChildren<{}>
>((props, ref) => {
  return <GoogleSheetsIcon ref={ref} {...props} />;
});
