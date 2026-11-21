import type { Branch, Data, Tab } from "../lib/types";
export type Ctx = {
  data: Data; busy: boolean; query: string; clearQuery: () => void;
  go: (tab: Tab, query?: string) => void; refresh: () => void;
  run: (action: () => Promise<unknown>, success: string) => Promise<boolean>;
  openCreate: () => void; openResolve: (b: Branch) => void; openWrite: (b: Branch) => void; openDiff: (b: Branch) => void; openInspector: (index: number) => void;
};
