// Mock for SVG and JSX files
import React from "react";

const SvgMock = React.forwardRef<SVGSVGElement>((props, ref) => (
  <svg ref={ref} {...props} />
));

SvgMock.displayName = "SvgMock";

export default SvgMock;
