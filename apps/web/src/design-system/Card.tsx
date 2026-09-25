import { HTMLAttributes, ReactNode } from "react";
import { Label } from "./Label";
import "./card.css";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  label?: string | string[];
  title?: string;
  children?: ReactNode;
  footer?: ReactNode;
}

export function Card({ label, title, children, footer, className, ...rest }: CardProps) {
  const parts = Array.isArray(label) ? label : label ? [label] : undefined;
  return (
    <div className={["ds-card", className].filter(Boolean).join(" ")} {...rest}>
      {parts && <Label parts={parts} />}
      {title && <h3 className="ds-card__title">{title}</h3>}
      {children && <div className="ds-card__body">{children}</div>}
      {footer && <div className="ds-card__footer">{footer}</div>}
    </div>
  );
}
