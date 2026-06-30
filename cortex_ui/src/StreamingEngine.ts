// cortex_ui/src/StreamingEngine.ts

import { useEffect, useRef, useState } from "react";

export class PieceTable {
  private original: string = "";
  private addBuffer: string = "";
  private entries: Array<{
    source: "original" | "add";
    start: number;
    length: number;
  }> = [];

  constructor(initialText: string = "") {
    this.original = initialText;
    if (initialText.length > 0) {
      this.entries.push({ source: "original", start: 0, length: initialText.length });
    }
  }

  public append(text: string): void {
    const start = this.addBuffer.length;
    this.addBuffer += text;
    this.entries.push({ source: "add", start, length: text.length });
  }

  public getSequence(): string {
    let result = "";
    for (const entry of this.entries) {
      const sourceStr = entry.source === "original" ? this.original : this.addBuffer;
      result += sourceStr.substring(entry.start, entry.start + entry.length);
    }
    return result;
  }
}

export class FenwickTree {
  private tree: Float64Array;

  constructor(size: number) {
    this.tree = new Float64Array(size + 1);
  }

  public add(index: number, deltaHeight: number): void {
    for (let i = index + 1; i < this.tree.length; i += i & -i) {
      this.tree[i] += deltaHeight;
    }
  }

  public getPrefixSum(index: number): number {
    let sum = 0;
    for (let i = index + 1; i > 0; i -= i & -i) {
      sum += this.tree[i];
    }
    return sum;
  }
}

export class CommitScheduler {
  private pendingBuffer: string = "";
  private isCommitScheduled: boolean = false;
  private onFlush: (text: string) => void;
  private onSync: () => void;

  constructor(onFlush: (text: string) => void, onSync: () => void) {
    this.onFlush = onFlush;
    this.onSync = onSync;
  }

  public appendToken(token: string): void {
    this.pendingBuffer += token;
    this.scheduleCommit();
  }

  private scheduleCommit(): void {
    if (this.isCommitScheduled) return;
    this.isCommitScheduled = true;

    requestAnimationFrame(async () => {
      const navScheduling = (navigator as any).scheduling;
      const winScheduler = (window as any).scheduler;

      if (navScheduling?.isInputPending?.()) {
        this.isCommitScheduled = false;
        if (winScheduler?.yield) {
          await winScheduler.yield();
        }
        this.scheduleCommit();
        return;
      }

      if (this.pendingBuffer.length > 0) {
        this.onFlush(this.pendingBuffer);
        this.pendingBuffer = "";
      }

      this.onSync();
      this.isCommitScheduled = false;
    });
  }
}

export class LRUCache<K, V> {
  private cache = new Map<K, V>();
  private maxEntries: number;

  constructor(maxEntries = 1000) {
    this.maxEntries = maxEntries;
  }

  public has(key: K): boolean {
    return this.cache.has(key);
  }

  public get(key: K): V | undefined {
    const value = this.cache.get(key);
    if (value !== undefined) {
      this.cache.delete(key);
      this.cache.set(key, value);
    }
    return value;
  }

  public set(key: K, value: V): void {
    if (this.cache.size >= this.maxEntries) {
      const oldestKey = this.cache.keys().next().value;
      if (oldestKey !== undefined) {
        this.cache.delete(oldestKey);
      }
    }
    this.cache.set(key, value);
  }
}

export class OffThreadRenderer {
  private lruCache = new LRUCache<string, string>(1000);

  public async renderMath(tex: string, displayMode: boolean): Promise<string> {
    const key = `${tex}:${displayMode}`;
    if (this.lruCache.has(key)) {
      return this.lruCache.get(key)!;
    }

    let html = "";
    if (displayMode) {
      html = `<div class="math-display">$$\n${tex}\n$$</div>`;
    } else {
      html = `<span class="math-inline">$${tex}$</span>`;
    }

    this.lruCache.set(key, html);
    return html;
  }

  public async renderCode(code: string, lang: string): Promise<string> {
    const key = `${code}:${lang}`;
    if (this.lruCache.has(key)) {
      return this.lruCache.get(key)!;
    }

    const escaped = code
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
    const html = `<pre class="code-block"><code class="language-${lang}">${escaped}</code></pre>`;

    this.lruCache.set(key, html);
    return html;
  }
}

export class ViewportStabilizer {
  private heightTree: FenwickTree;
  private container: HTMLElement;

  constructor(container: HTMLElement, size: number) {
    this.container = container;
    this.heightTree = new FenwickTree(size);
  }

  public registerBlockResize(blockIndex: number, realHeight: number, estimatedHeight: number): void {
    if (realHeight === estimatedHeight) return;

    const delta = realHeight - estimatedHeight;
    const blockTopOffset = this.heightTree.getPrefixSum(blockIndex - 1);
    const currentScrollTop = this.container.scrollTop;

    if (blockTopOffset < currentScrollTop) {
      this.container.scrollTop += delta;
    }

    this.heightTree.add(blockIndex, delta);
  }
}

export class ScrollSentinel {
  private sentinel: HTMLElement;
  private container: HTMLElement;
  private isUserAtBottom: boolean = true;
  private observer: IntersectionObserver;

  constructor(container: HTMLElement, sentinel: HTMLElement) {
    this.container = container;
    this.sentinel = sentinel;

    this.observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        this.isUserAtBottom = entry.isIntersecting;
      }
    }, {
      root: this.container,
      threshold: 0.1
    });

    this.observer.observe(this.sentinel);
  }

  public evaluateScrollTrigger(): void {
    const selection = window.getSelection();
    if (selection && selection.toString().length > 0) {
      return;
    }

    if (this.isUserAtBottom) {
      this.sentinel.scrollIntoView({ behavior: "instant" as any, block: "end" });
    }
  }

  public disconnect(): void {
    this.observer.disconnect();
  }
}

export function useStreamingEngine(
  containerRef: React.RefObject<HTMLDivElement | null>,
  sentinelRef: React.RefObject<HTMLDivElement | null>
) {
  const [text, setText] = useState("");
  const pieceTableRef = useRef<PieceTable>(new PieceTable());
  const schedulerRef = useRef<CommitScheduler | null>(null);
  const sentinelInstanceRef = useRef<ScrollSentinel | null>(null);

  useEffect(() => {
    if (!containerRef.current || !sentinelRef.current) return;

    sentinelInstanceRef.current = new ScrollSentinel(containerRef.current, sentinelRef.current);

    schedulerRef.current = new CommitScheduler(
      (chunk) => {
        pieceTableRef.current.append(chunk);
        setText(pieceTableRef.current.getSequence());
      },
      () => {
        if (sentinelInstanceRef.current) {
          sentinelInstanceRef.current.evaluateScrollTrigger();
        }
      }
    );

    return () => {
      if (sentinelInstanceRef.current) {
        sentinelInstanceRef.current.disconnect();
      }
    };
  }, [containerRef, sentinelRef]);

  const appendToken = (token: string) => {
    if (schedulerRef.current) {
      schedulerRef.current.appendToken(token);
    }
  };

  return { text, appendToken };
}
