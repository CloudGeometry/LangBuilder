import React, { forwardRef } from "react";
import SharePointIcon from "./SharePoint";

export const SharePoint = forwardRef<
  SVGSVGElement,
  React.PropsWithChildren<{}>
>((props, ref) => {
  return <SharePointIcon ref={ref} {...props} />;
});
