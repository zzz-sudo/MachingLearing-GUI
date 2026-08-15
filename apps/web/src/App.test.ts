import { describe, expect, it } from "vitest";
import type { ProjectFileNode } from "@ml-gui/contracts";
import { filterProjectTree } from "./App";

const projectTree: ProjectFileNode[] = [
  {
    name: ".cache",
    relativePath: ".cache",
    kind: "directory",
    hidden: true,
    children: [
      {
        name: "state.json",
        relativePath: ".cache/state.json",
        kind: "file",
        hidden: false,
        size: 12,
        children: [],
      },
    ],
  },
  {
    name: "documents",
    relativePath: "documents",
    kind: "directory",
    hidden: false,
    children: [
      {
        name: "销售报告.md",
        relativePath: "documents/销售报告.md",
        kind: "file",
        hidden: false,
        size: 128,
        children: [],
      },
    ],
  },
];

describe("filterProjectTree", () => {
  it("keeps the matching file and its directory hierarchy", () => {
    const result = filterProjectTree(projectTree, "销售");

    expect(result).toHaveLength(1);
    expect(result[0]?.name).toBe("documents");
    expect(result[0]?.children[0]?.relativePath).toBe("documents/销售报告.md");
  });

  it("finds hidden files by name", () => {
    const result = filterProjectTree(projectTree, "state");

    expect(result[0]?.hidden).toBe(true);
    expect(result[0]?.children[0]?.name).toBe("state.json");
  });
});
