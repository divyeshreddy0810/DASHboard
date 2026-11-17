import { useEffect, useState } from "react";

interface Props {
  value: string;
  onSave: (title: string) => Promise<void>;
}

export function TitleEditor({ value, onSave }: Props) {
  const [draft, setDraft] = useState(value);
  const [saving, setSaving] = useState(false);

  useEffect(() => setDraft(value), [value]);

  const commit = async () => {
    const next = draft.trim();
    if (!next || next === value) {
      setDraft(value);
      return;
    }
    setSaving(true);
    try {
      await onSave(next);
    } catch {
      setDraft(value);
    } finally {
      setSaving(false);
    }
  };

  return (
    <input
      className="title-input"
      aria-label="Dashboard title"
      value={draft}
      maxLength={120}
      disabled={saving}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === "Enter") e.currentTarget.blur();
        if (e.key === "Escape") {
          setDraft(value);
          e.currentTarget.blur();
        }
      }}
    />
  );
}
