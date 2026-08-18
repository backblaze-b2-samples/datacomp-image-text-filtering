"use client";

import { toast } from "sonner";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { RunForm, type RunFormValues } from "./run-form";
import { useSourcePrefixes, useUpdateRun } from "@/lib/queries";
import type { FilterRun } from "@datacomp-image-text-filtering/shared";

interface EditRunDialogProps {
  run: FilterRun;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/** Edit a PENDING run's config. Completed/running runs are immutable — the
 * detail view offers "Clone" instead. */
export function EditRunDialog({ run, open, onOpenChange }: EditRunDialogProps) {
  const prefixesQuery = useSourcePrefixes({ enabled: open });
  const prefixes = prefixesQuery.data ?? [];
  const update = useUpdateRun(run.id);

  const defaults: RunFormValues = {
    name: run.config.name,
    source_prefix: run.config.source_prefix,
    clip_model: run.config.clip_model,
    strategy: run.config.strategy,
    clip_percentile: run.config.clip_percentile,
    min_resolution: run.config.min_resolution,
    caption_min_tokens: run.config.caption_min_tokens,
    caption_max_tokens: run.config.caption_max_tokens,
    dedup: run.config.dedup,
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Edit run</DialogTitle>
          <DialogDescription>
            Change this pending run&apos;s config before you start it.
          </DialogDescription>
        </DialogHeader>
        <RunForm
          mode="edit"
          key={run.updated_at}
          defaultValues={defaults}
          prefixes={prefixes.length > 0 ? prefixes : [{ prefix: run.config.source_prefix, shard_count: 0 }]}
          submitting={update.isPending}
          onCancel={() => onOpenChange(false)}
          onSubmit={(config) =>
            update.mutate(config, {
              onSuccess: () => {
                toast.success("Run updated");
                onOpenChange(false);
              },
              onError: (e) =>
                toast.error("Couldn't update run", { description: e.message }),
            })
          }
        />
      </DialogContent>
    </Dialog>
  );
}
