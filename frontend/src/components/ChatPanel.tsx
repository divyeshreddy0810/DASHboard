import { useEffect, useRef, useState } from "react";
import type { ChatMessage } from "../types";

interface Props {
  history: ChatMessage[];
  busy: boolean;
  disabled?: string;
  onSend: (message: string) => void;
}

const SUGGESTIONS = [
  "Break the main chart down by another category",
  "Only show the last 6 months",
  "Replace the pie chart with a bar chart",
];

export function ChatPanel({ history, busy, disabled, onSend }: Props) {
  const [text, setText] = useState("");
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [history.length, busy]);

  const submit = (message: string) => {
    const m = message.trim();
    if (!m || busy) return;
    onSend(m);
    setText("");
  };

  return (
    <section className="chat">
      <h2>Edit with chat</h2>
      <div className="chat-log" ref={listRef}>
        {history.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>{m.content}</div>
        ))}
        {busy && <div className="msg assistant pending">Updating the dashboard…</div>}
      </div>
      {disabled ? (
        <p className="chat-note">{disabled}</p>
      ) : (
        <>
          {history.length <= 1 && (
            <div className="suggestions">
              {SUGGESTIONS.map((s) => (
                <button key={s} type="button" onClick={() => submit(s)} disabled={busy}>{s}</button>
              ))}
            </div>
          )}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              submit(text);
            }}
          >
            <textarea
              value={text}
              rows={3}
              placeholder="e.g. show revenue by channel as a stacked bar"
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  submit(text);
                }
              }}
            />
            <button type="submit" disabled={busy || !text.trim()}>Send</button>
          </form>
        </>
      )}
    </section>
  );
}
