export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  /** Set when a format-specific extractor was skipped or failed (e.g. an image
   *  above the decompression-bomb decode limit). Core fields stay exact. */
  metadata_warning: string | null;
  // Image-specific
  image_width: number | null;
  image_height: number | null;
  exif: Record<string, string> | null;
  // PDF-specific
  pdf_pages: number | null;
  pdf_author: string | null;
  pdf_title: string | null;
  // Audio/Video
  duration_seconds: number | null;
  codec: string | null;
  bitrate: number | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

/** A short-lived presigned PUT the browser uploads a file directly to B2 with.
 *  `headers` are signed into the URL, so the browser must send them verbatim. */
export interface PresignUploadResponse {
  key: string;
  url: string;
  method: string;
  content_type: string;
  headers: Record<string, string>;
  expires_in: number;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// --- Filter Runs (the primary entity) ------------------------------------

export type FilterStrategy =
  | "clip_score"
  | "basic"
  | "image_based"
  | "text_based";
export type ClipModelName = "ViT-B-32" | "ViT-L-14";
export type RunStatus = "pending" | "running" | "completed" | "failed";

export interface RunConfig {
  name: string;
  source_prefix: string;
  clip_model: ClipModelName;
  strategy: FilterStrategy;
  /** Fraction of pairs to KEEP (top-scoring). 0.30 = DataComp clip_score default. */
  clip_percentile: number;
  min_resolution: number;
  caption_min_tokens: number;
  caption_max_tokens: number;
  dedup: boolean;
}

export interface ShardMetric {
  shard: string;
  pairs_in: number;
  pairs_kept: number;
  pairs_dropped: number;
  mean_clip_score: number;
  kept_mean_clip_score: number;
  output_key: string | null;
  metrics_key: string | null;
}

export interface FilterStats {
  total_pairs_in: number;
  total_pairs_kept: number;
  total_pairs_dropped: number;
  reduction_pct: number;
  mean_clip_score: number;
  clip_score_threshold: number | null;
  device: string | null;
}

export interface FilterRun {
  id: string;
  config: RunConfig;
  status: RunStatus;
  created_at: string;
  updated_at: string;
  source_shard_count: number;
  output_prefix: string | null;
  metrics_prefix: string | null;
  shard_metrics: ShardMetric[];
  stats: FilterStats | null;
  error: string | null;
}

export interface DeleteRunResponse {
  deleted: boolean;
  id: string;
}

export interface SourcePrefix {
  prefix: string;
  shard_count: number;
}

export interface RunStats {
  total_runs: number;
  completed_runs: number;
  running_runs: number;
  failed_runs: number;
  total_pairs_kept: number;
  total_pairs_dropped: number;
  avg_reduction_pct: number;
}

// --- Pool Explorer -------------------------------------------------------

export interface ShardSummary {
  key: string;
  name: string;
  size_bytes: number;
  size_human: string;
  scope: string;
  run_id: string | null;
}

export interface ImageTextPair {
  key: string;
  caption: string;
  thumbnail_data_url: string | null;
  width: number | null;
  height: number | null;
  clip_score: number | null;
  kept: boolean | null;
}

export interface ShardContents {
  key: string;
  scope: string;
  pair_count: number;
  shown: number;
  pairs: ImageTextPair[];
}
