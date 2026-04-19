import { Separator } from "react-resizable-panels";

export function ResizeHandle() {
  return (
    <Separator className="ResizeHandle">
      <div className="ResizeHandleInner" />
    </Separator>
  );
}
