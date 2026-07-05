/**
 * Purpose: Client-side PDF upload form with validation and status feedback.
 * Interactions: Used by document-dashboard.tsx. Calls uploadDocument() in
 * lib/api.ts, then reports the uploaded document to the shared dashboard state.
 */
"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import type { Document } from "@/lib/api";
import { uploadDocument } from "@/lib/api";

type UploadState = "idle" | "uploading" | "success" | "error";

type DocumentUploadProps = {
  onUploaded?: (document: Document) => void;
};

export function DocumentUpload({ onUploaded }: DocumentUploadProps) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [message, setMessage] = useState<string | null>(null);

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(file);
    setUploadState("idle");
    setMessage(null);
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedFile) {
      setUploadState("error");
      setMessage("Choose a PDF file before uploading.");
      return;
    }

    if (!selectedFile.name.toLowerCase().endsWith(".pdf")) {
      setUploadState("error");
      setMessage("Only PDF files are allowed.");
      return;
    }

    setUploadState("uploading");
    setMessage(null);

    const { data, error } = await uploadDocument(selectedFile);

    if (error || !data) {
      setUploadState("error");
      setMessage(error ?? "Upload failed.");
      return;
    }

    setUploadState("success");
    setMessage(`Uploaded "${data.original_filename}".`);
    setSelectedFile(null);
    onUploaded?.(data);

    if (inputRef.current) {
      inputRef.current.value = "";
    }

    router.refresh();
  }

  return (
    <form className="upload-form" onSubmit={handleSubmit}>
      <label className="field-label" htmlFor="pdf-upload">
        Aviation PDF
      </label>
      <input
        ref={inputRef}
        id="pdf-upload"
        className="file-input"
        type="file"
        accept="application/pdf,.pdf"
        onChange={handleFileChange}
        disabled={uploadState === "uploading"}
      />
      {selectedFile && (
        <p className="helper-text">
          Selected: {selectedFile.name} ({Math.ceil(selectedFile.size / 1024)} KB)
        </p>
      )}
      <button
        className="button primary"
        type="submit"
        disabled={uploadState === "uploading" || !selectedFile}
      >
        {uploadState === "uploading" ? "Uploading..." : "Upload PDF"}
      </button>
      {uploadState === "uploading" && (
        <p className="helper-text">Saving file and metadata...</p>
      )}
      {message && (
        <p className={uploadState === "error" ? "error-text" : "success-text"}>
          {message}
        </p>
      )}
    </form>
  );
}
