"use client";

import { CheckCircle2, Loader2, UploadCloud } from "lucide-react";
import { useRef, useState } from "react";

import { useUploadDocument } from "@/hooks/useSources";
import { ApiError } from "@/lib/api";
import { useToast } from "@/lib/toast";
import { Button } from "@/components/ui/Button";

export function UploadPanel({ projectId }: { projectId: string }) {
  const upload = useUploadDocument(projectId);
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  async function handleFiles(files: FileList | null) {
    const file = files?.[0];
    if (!file) return;
    try {
      const result = await upload.mutateAsync({ file });
      toast({
        title: "Upload received",
        description: `"${file.name}" is being scanned, parsed, and indexed.`,
        variant: "success",
      });
      void result;
    } catch (err) {
      toast({
        title: "Upload failed",
        description: err instanceof ApiError ? String(err.detail ?? err.message) : "Please try again.",
        variant: "danger",
      });
    }
  }

  return (
    <div
      className="card"
      style={{
        padding: "var(--space-5)",
        borderStyle: dragging ? "dashed" : "solid",
        borderColor: dragging ? "var(--color-brand-600)" : undefined,
        background: dragging ? "var(--color-brand-50)" : undefined,
      }}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        void handleFiles(e.dataTransfer.files);
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)" }}>
        <span
          style={{
            display: "grid",
            placeItems: "center",
            width: "2.75rem",
            height: "2.75rem",
            borderRadius: "var(--radius-lg)",
            background: "var(--color-brand-50)",
            color: "var(--color-brand-700)",
            flexShrink: 0,
          }}
        >
          {upload.isPending ? <Loader2 size={20} className="animate-spin" aria-hidden /> : <UploadCloud size={20} aria-hidden />}
        </span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ margin: 0, fontWeight: "var(--font-weight-medium)" }}>Upload a document</p>
          <p style={{ margin: 0, fontSize: "var(--font-size-xs)", color: "var(--text-tertiary)" }}>
            PDF, DOCX, XLSX, TXT, or an image (OCR). Scanned for malware before indexing.
          </p>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          style={{ display: "none" }}
          onChange={(e) => {
            void handleFiles(e.target.files);
            e.target.value = "";
          }}
        />
        <Button variant="secondary" size="small" onClick={() => fileInputRef.current?.click()} loading={upload.isPending}>
          Browse
        </Button>
      </div>
      {upload.isSuccess && (
        <p style={{ margin: "var(--space-3) 0 0", fontSize: "var(--font-size-xs)", color: "var(--color-success-700)", display: "flex", alignItems: "center", gap: "var(--space-1)" }}>
          <CheckCircle2 size={13} aria-hidden /> Indexed and searchable — evidence typically appears within a few seconds.
        </p>
      )}
    </div>
  );
}
