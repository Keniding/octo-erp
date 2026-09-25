import { InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";
import "./field.css";

interface FieldWrapProps {
  label: string;
  hint?: string;
  children: ReactNode;
}

export function FieldWrap({ label, hint, children }: FieldWrapProps) {
  return (
    <label className="ds-field">
      <span className="ds-field__label">{label}</span>
      {children}
      {hint && <span className="ds-field__hint">{hint}</span>}
    </label>
  );
}

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: string;
}

export function Input({ label, hint, ...rest }: InputProps) {
  return (
    <FieldWrap label={label} hint={hint}>
      <input className="ds-field__control" {...rest} />
    </FieldWrap>
  );
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  hint?: string;
}

export function Select({ label, hint, children, ...rest }: SelectProps) {
  return (
    <FieldWrap label={label} hint={hint}>
      <select className="ds-field__control" {...rest}>
        {children}
      </select>
    </FieldWrap>
  );
}
