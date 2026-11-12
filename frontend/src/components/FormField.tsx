interface FormFieldProps {
  id: string
  label: string
  value: string
  onChange: (value: string) => void
  type?: 'text' | 'email' | 'password'
  autoComplete?: string
  required?: boolean
  minLength?: number
  hint?: string
}

export function FormField({
  id,
  label,
  value,
  onChange,
  type = 'text',
  autoComplete,
  required = false,
  minLength,
  hint,
}: FormFieldProps) {
  const hintId = hint ? `${id}-hint` : undefined

  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        name={id}
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        autoComplete={autoComplete}
        required={required}
        minLength={minLength}
        aria-describedby={hintId}
      />
      {hint && (
        <p className="field-hint" id={hintId}>
          {hint}
        </p>
      )}
    </div>
  )
}
