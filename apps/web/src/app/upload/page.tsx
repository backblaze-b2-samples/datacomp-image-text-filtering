import { UploadForm } from "@/components/upload/upload-form";

export default function UploadPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Ingest</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground text-pretty">
          Upload raw WebDataset shards or image-text assets straight into B2. The
          browser uploads directly to the bucket with a presigned PUT — bytes
          never traverse the API, so there is no serverless payload ceiling. Up to
          100 MB per file.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <UploadForm />
      </div>
    </div>
  );
}
