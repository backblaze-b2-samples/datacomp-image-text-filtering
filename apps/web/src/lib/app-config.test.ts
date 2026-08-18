import { describe, expect, it } from "vitest";
import { APP_DESCRIPTION, APP_NAME } from "@/lib/app-config";

describe("app identity", () => {
  it("ships the canonical app name and description", () => {
    expect(APP_NAME).toBe("DataComp Image-Text Filtering");
    expect(APP_DESCRIPTION).toBe(
      "DataComp-style image-text dataset curation on Backblaze B2: filter WebDataset shards by CLIP alignment"
    );
  });
});
