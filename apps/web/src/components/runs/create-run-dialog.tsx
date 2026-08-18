"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { RunForm, CREATE_DEFAULTS } from "./run-form";
import { useCreateRun, useSourcePrefixes } from "@/lib/queries";

export function CreateRunDialog({ label = "New run" }: { label?: string }) {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const prefixesQuery = useSourcePrefixes({ enabled: open });
  const prefixes = prefixesQuery.data ?? [];
  const create = useCreateRun();

  const defaults = {
    ...CREATE_DEFAULTS,
    source_prefix: prefixes[0]?.prefix ?? "pool/",
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" className="h-8">
          <Plus className="h-3.5 w-3.5" />
          {label}
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>New Filter Run</DialogTitle>
          <DialogDescription>
            Configure a DataComp-style CLIP filter over a pool of image-text shards.
          </DialogDescription>
        </DialogHeader>
        <RunForm
          mode="create"
          key={open ? prefixes.length : "closed"}
          defaultValues={defaults}
          prefixes={prefixes}
          submitting={create.isPending}
          onCancel={() => setOpen(false)}
          onSubmit={(config) =>
            create.mutate(config, {
              onSuccess: (run) => {
                toast.success("Run created", {
                  description: "Start it to filter the pool with CLIP.",
                });
                setOpen(false);
                router.push(`/runs/${run.id}`);
              },
              onError: (e) =>
                toast.error("Couldn't create run", { description: e.message }),
            })
          }
        />
      </DialogContent>
    </Dialog>
  );
}
