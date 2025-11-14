import type React from "react";
import { forwardRef } from "react";
import NotionIcon from "./Notion";

export const Notion = forwardRef<
  SVGSVGElement,
  React.PropsWithChildren<{}>
>((props, ref) => {
  return <NotionIcon ref={ref} {...props} />;
});
