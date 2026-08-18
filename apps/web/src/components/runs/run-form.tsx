"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import type { RunConfig, SourcePrefix } from "@datacomp-image-text-filtering/shared";

const STRATEGIES = [
  {
    value: "clip_score",
    label: "CLIP score",
    hint: "Keep the top-percentile pairs by CLIP alignment (DataComp default).",
  },
  {
    value: "basic",
    label: "Basic",
    hint: "CLIP score AND min resolution AND caption-length bounds.",
  },
  { value: "image_based", label: "Image based", hint: "Min resolution only." },
  { value: "text_based", label: "Text based", hint: "Caption-length bounds only." },
] as const;

const schema = z.object({
  name: z.string().min(1, "Name is required").max(100),
  source_prefix: z.string().min(1),
  clip_model: z.enum(["ViT-B-32", "ViT-L-14"]),
  strategy: z.enum(["clip_score", "basic", "image_based", "text_based"]),
  clip_percentile: z.coerce.number().min(0).max(1),
  min_resolution: z.coerce.number().int().min(1).max(8192),
  caption_min_tokens: z.coerce.number().int().min(0).max(1000),
  caption_max_tokens: z.coerce.number().int().min(1).max(100000),
  dedup: z.boolean(),
});

export type RunFormValues = z.infer<typeof schema>;

export const CREATE_DEFAULTS: RunFormValues = {
  name: "",
  source_prefix: "pool/",
  clip_model: "ViT-B-32",
  strategy: "clip_score",
  clip_percentile: 0.3,
  min_resolution: 64,
  caption_min_tokens: 2,
  caption_max_tokens: 256,
  dedup: true,
};

interface RunFormProps {
  mode: "create" | "edit";
  defaultValues: RunFormValues;
  prefixes: SourcePrefix[];
  submitting: boolean;
  onSubmit: (config: RunConfig) => void;
  onCancel: () => void;
}

/**
 * Create/edit form for a Filter Run. Every finite-value field is a selector
 * (Select / RadioGroup / Switch); only the run name is free text. On the create
 * form, safe defaults are surfaced as guidance via FormDescription (never an
 * autofill button). Mirrors the settings-form.tsx pattern.
 */
export function RunForm({
  mode,
  defaultValues,
  prefixes,
  submitting,
  onSubmit,
  onCancel,
}: RunFormProps) {
  const form = useForm<RunFormValues>({
    resolver: zodResolver(schema),
    defaultValues,
  });
  const isCreate = mode === "create";
  const options = prefixes.length > 0 ? prefixes : [{ prefix: "pool/", shard_count: 0 }];

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit((values) => onSubmit(values))}
        className="space-y-5"
      >
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Run name</FormLabel>
              <FormControl>
                <Input placeholder="nightly-clip30" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="source_prefix"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Source pool</FormLabel>
              <Select onValueChange={field.onChange} value={field.value}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {options.map((p) => (
                    <SelectItem key={p.prefix} value={p.prefix}>
                      {p.prefix} ({p.shard_count} shard
                      {p.shard_count === 1 ? "" : "s"})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormDescription>
                Raw WebDataset shards to filter. Seed with{" "}
                <code>services/api/scripts/seed_pool.py</code>.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="clip_model"
          render={({ field }) => (
            <FormItem>
              <FormLabel>CLIP model</FormLabel>
              <Select onValueChange={field.onChange} value={field.value}>
                <FormControl>
                  <SelectTrigger className="w-60">
                    <SelectValue />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  <SelectItem value="ViT-B-32">ViT-B-32 (fast, ~350 MB)</SelectItem>
                  <SelectItem value="ViT-L-14">ViT-L-14 (DataComp large)</SelectItem>
                </SelectContent>
              </Select>
              {isCreate && (
                <FormDescription>
                  ViT-B-32 (OpenAI weights) is the ungated, keyless default.
                </FormDescription>
              )}
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="strategy"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Filter strategy</FormLabel>
              <FormControl>
                <RadioGroup
                  onValueChange={field.onChange}
                  value={field.value}
                  className="grid gap-2"
                >
                  {STRATEGIES.map((s) => (
                    <label
                      key={s.value}
                      className="flex items-start gap-2 rounded-md border border-border p-2.5 text-sm cursor-pointer"
                    >
                      <RadioGroupItem value={s.value} className="mt-0.5" />
                      <span>
                        <span className="font-medium">{s.label}</span>
                        <span className="block text-xs text-muted-foreground">
                          {s.hint}
                        </span>
                      </span>
                    </label>
                  ))}
                </RadioGroup>
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="grid gap-5 sm:grid-cols-2">
          <FormField
            control={form.control}
            name="clip_percentile"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Keep fraction (CLIP percentile)</FormLabel>
                <FormControl>
                  <Input
                    type="number"
                    min={0}
                    max={1}
                    step={0.05}
                    className="font-mono tabular-nums"
                    {...field}
                  />
                </FormControl>
                {isCreate && (
                  <FormDescription>
                    0.30 — top 30% by CLIP score, DataComp&apos;s clip_score default.
                  </FormDescription>
                )}
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="min_resolution"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Min resolution (px)</FormLabel>
                <FormControl>
                  <Input type="number" min={1} className="font-mono tabular-nums" {...field} />
                </FormControl>
                {isCreate && <FormDescription>64 px is a safe default.</FormDescription>}
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="caption_min_tokens"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Caption min tokens</FormLabel>
                <FormControl>
                  <Input type="number" min={0} className="font-mono tabular-nums" {...field} />
                </FormControl>
                {isCreate && <FormDescription>2 tokens.</FormDescription>}
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="caption_max_tokens"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Caption max tokens</FormLabel>
                <FormControl>
                  <Input type="number" min={1} className="font-mono tabular-nums" {...field} />
                </FormControl>
                {isCreate && <FormDescription>256 tokens.</FormDescription>}
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <FormField
          control={form.control}
          name="dedup"
          render={({ field }) => (
            <FormItem className="flex flex-row items-center justify-between rounded-md border border-border p-3">
              <div className="space-y-0.5">
                <FormLabel>Near-duplicate removal</FormLabel>
                {isCreate && (
                  <FormDescription>
                    On by default — drops near-duplicate images (average-hash).
                  </FormDescription>
                )}
              </div>
              <FormControl>
                <Switch checked={field.value} onCheckedChange={field.onChange} />
              </FormControl>
            </FormItem>
          )}
        />

        <div className="flex items-center justify-end gap-2">
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting ? "Saving..." : isCreate ? "Create run" : "Save changes"}
          </Button>
        </div>
      </form>
    </Form>
  );
}
