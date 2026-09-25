import { ButtonHTMLAttributes } from "react";
import "./button.css";

type Variant = "primary" | "secondary" | "ghost";
type Size = "md" | "sm";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

export function Button({ variant = "secondary", size = "md", className, children, ...rest }: ButtonProps) {
  const classes = ["ds-button", `ds-button--${variant}`, `ds-button--${size}`, className]
    .filter(Boolean)
    .join(" ");
  return (
    <button className={classes} {...rest}>
      {children}
    </button>
  );
}
