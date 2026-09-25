import { HTMLAttributes, ReactNode } from "react";
import "./grid-paper.css";

interface GridPaperProps extends HTMLAttributes<HTMLDivElement> {
  children?: ReactNode;
  registration?: boolean;
  minHeight?: number | string;
}

export function GridPaper({
  children,
  registration = true,
  minHeight,
  className,
  style,
  ...rest
}: GridPaperProps) {
  return (
    <div
      className={["ds-grid-paper", className].filter(Boolean).join(" ")}
      style={{ minHeight, ...style }}
      {...rest}
    >
      {registration && (
        <>
          <span className="ds-grid-paper__reg ds-grid-paper__reg--tl">+</span>
          <span className="ds-grid-paper__reg ds-grid-paper__reg--tr">+</span>
          <span className="ds-grid-paper__reg ds-grid-paper__reg--bl">+</span>
          <span className="ds-grid-paper__reg ds-grid-paper__reg--br">+</span>
        </>
      )}
      <div className="ds-grid-paper__content">{children}</div>
    </div>
  );
}
