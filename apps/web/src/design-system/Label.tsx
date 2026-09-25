import "./label.css";

type Tone = "muted" | "ink" | "accent";

interface LabelProps {
  parts?: string[];
  children?: string;
  tone?: Tone;
}

export function Label({ parts, children, tone = "muted" }: LabelProps) {
  const segments = parts ?? (children ? [children] : []);
  return (
    <span className={`ds-label ds-label--${tone}`}>
      {segments.map((s) => s.toUpperCase()).join(" // ")}
    </span>
  );
}
