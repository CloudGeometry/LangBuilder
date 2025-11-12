// Mock for react-markdown
import React from "react";

const Markdown: React.FC<{ children?: React.ReactNode }> = ({ children }) => (
  <div data-testid="markdown-mock">{children}</div>
);

export default Markdown;
