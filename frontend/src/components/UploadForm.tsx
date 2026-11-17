import { useRef, useState } from "react";

interface Props {
  busy: boolean;
  onSubmit: (file: File, title: string, goal: string) => void;
}

export function UploadForm({ busy, onSubmit }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [goal, setGoal] = useState("");
  const [dragging, setDragging] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  return (
    <form
      className="upload"
      onSubmit={(e) => {
        e.preventDefault();
        if (file && title.trim()) onSubmit(file, title.trim(), goal);
      }}
    >
      <div
        className={`dropzone${dragging ? " over" : ""}`}
        onClick={() => input.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
        }}
      >
        <input
          ref={input}
          type="file"
          accept=".csv,.tsv,.txt,.xlsx,.xls,.json"
          hidden
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        {file ? (
          <strong>{file.name}</strong>
        ) : (
          <>
            <strong>Drop a file here or click to choose</strong>
            <span>CSV, TSV, Excel or JSON</span>
          </>
        )}
      </div>
      <label>
        Dashboard title
        <input
          type="text"
          value={title}
          required
          maxLength={120}
          placeholder="e.g. Q4 sales review"
          onChange={(e) => setTitle(e.target.value)}
        />
      </label>
      <label>
        What do you want to know? <span className="optional">(optional)</span>
        <input
          type="text"
          value={goal}
          placeholder="e.g. which regions and products drive profit"
          onChange={(e) => setGoal(e.target.value)}
        />
      </label>
      <button type="submit" disabled={!file || !title.trim() || busy}>
        {busy ? "Building dashboard…" : "Build dashboard"}
      </button>
    </form>
  );
}
