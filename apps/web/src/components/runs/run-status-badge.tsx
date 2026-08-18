import { Badge } from "@/components/ui/badge";
import { Loader2 } from "lucide-react";
import type { RunStatus } from "@datacomp-image-text-filtering/shared";

const VARIANT: Record<
  RunStatus,
  "default" | "secondary" | "destructive" | "outline"
> = {
  pending: "outline",
  running: "secondary",
  completed: "default",
  failed: "destructive",
};

export function RunStatusBadge({ status }: { status: RunStatus }) {
  return (
    <Badge variant={VARIANT[status]} className="capitalize">
      {status === "running" && (
        <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
      )}
      {status}
    </Badge>
  );
}
