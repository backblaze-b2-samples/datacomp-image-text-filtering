"use client";

import { toast } from "sonner";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useDeleteRun } from "@/lib/queries";
import type { FilterRun } from "@datacomp-image-text-filtering/shared";

interface DeleteRunDialogProps {
  run: FilterRun;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDeleted?: () => void;
}

export function DeleteRunDialog({
  run,
  open,
  onOpenChange,
  onDeleted,
}: DeleteRunDialogProps) {
  const del = useDeleteRun();

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete “{run.config.name}”?</AlertDialogTitle>
          <AlertDialogDescription>
            Removes this run&apos;s manifest and, scoped to this run only, its
            <code className="mx-1">filtered/{run.id}/</code> and
            <code className="mx-1">metrics/{run.id}/</code> artifacts. The raw
            pool and other runs are untouched. This cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            className="bg-destructive text-white hover:bg-destructive/90"
            onClick={(e) => {
              e.preventDefault();
              del.mutate(run.id, {
                onSuccess: () => {
                  toast.success("Run deleted");
                  onOpenChange(false);
                  onDeleted?.();
                },
                onError: (err) =>
                  toast.error("Couldn't delete run", { description: err.message }),
              });
            }}
          >
            {del.isPending ? "Deleting..." : "Delete run"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
