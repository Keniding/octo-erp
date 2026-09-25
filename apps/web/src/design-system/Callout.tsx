import { HTMLAttributes, ReactNode } from "react";
import "./callout.css";

type Tone = "note" | "valid" | "warning" | "critical";

const defaultWord: Record<Tone, string> = {
  note: "Nota",
  valid: "Validación",
  warning: "Advertencia",
  critical: "Crítico",
};

interface CalloutProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  tone: Tone;
  title?: string;
  children: ReactNode;
  word?: string;
}

export function Callout({ tone, title, children, word, className, ...rest }: CalloutProps) {
  return (
    <div
      className={["ds-callout", `ds-callout--${tone}`, className].filter(Boolean).join(" ")}
      role={tone === "critical" ? "alert" : "status"}
      {...rest}
    >
      <span className="ds-callout__word">{word ?? defaultWord[tone]}</span>
      {title && <strong className="ds-callout__title">{title}</strong>}
      <div className="ds-callout__body">{children}</div>
    </div>
  );
}
