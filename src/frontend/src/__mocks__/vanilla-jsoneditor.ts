// Mock for vanilla-jsoneditor to avoid Jest transformation issues
export class JSONEditor {
  constructor() {}
  set() {}
  update() {}
  updateProps() {}
  get() {
    return {};
  }
  getText() {
    return "";
  }
  setText() {}
  destroy() {}
}

export default { JSONEditor };
