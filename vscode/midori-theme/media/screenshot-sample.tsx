// Sample file for the Marketplace screenshots. Every line here exists to
// exercise one claim the README makes — see media/SCREENSHOTS.md.

import { useMemo, useState } from "react";

/** A ledger row, as it comes back from the API. */
export interface LedgerRow {
  id: number;
  label: string;
  amount: number;
  settled: boolean;
}

type Bucket = "income" | "expense" | "transfer";

const RATE = 0.0825;
const EMPTY: readonly LedgerRow[] = [];

export function classify(row: LedgerRow): Bucket {
  if (row.amount > 0) return "income";
  if (row.label.startsWith("xfer:")) return "transfer";
  return "expense";
}

export class Ledger {
  #rows: LedgerRow[] = [];

  add(row: LedgerRow): this {
    this.#rows.push(row);
    return this;
  }

  total(bucket?: Bucket): number {
    return this.#rows
      .filter((r) => !bucket || classify(r) === bucket)
      .reduce((sum, r) => sum + r.amount * (1 + RATE), 0);
  }

  // Markup inside a template literal — TypeScript gives this one scope end to
  // end, so without the grammar injection every tag here would be one colour.
  render(): string {
    const cls = this.#rows.length ? "ledger" : "ledger ledger--empty";
    return `
      <section class="${cls}" data-count="${this.#rows.length}">
        <h2 class="ledger__title">Ledger</h2>
        <ul role="list">
          ${this.#rows.map((r) => `<li data-id="${r.id}">${r.label}</li>`).join("")}
        </ul>
      </section>
    `;
  }
}

export function LedgerTable({ rows = EMPTY }: { rows?: readonly LedgerRow[] }) {
  const [bucket, setBucket] = useState<Bucket | null>(null);

  const visible = useMemo(() => {
    if (!bucket) return rows;
    return rows.filter((r) => classify(r) === bucket);
  }, [rows, bucket]);

  return (
    <table className="ledger">
      <tbody>
        {visible.map((row) => (
          <tr key={row.id} onClick={() => setBucket(classify(row))}>
            <td>{row.label}</td>
            <td className={row.settled ? "is-settled" : "is-open"}>
              {row.amount.toFixed(2)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
