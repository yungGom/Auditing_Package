from __future__ import annotations
import argparse
import pandas as pd
from logic_jet import load_gl_for_jet
from logic_comparison import load_tb, perform_roll_forward_test


def main() -> None:
    """Command line utility to verify prior TB + GL = current TB."""
    parser = argparse.ArgumentParser(
        description="Verify that prior trial balance and journal entries roll forward to the current trial balance"
    )
    parser.add_argument("--gl", required=True, help="Path to the general ledger file (csv or xlsx)")
    parser.add_argument("--prev", required=True, help="Path to the prior trial balance file (csv or xlsx)")
    parser.add_argument("--curr", required=True, help="Path to the current trial balance file (csv or xlsx)")
    parser.add_argument("--gl-header", type=int, default=0, help="Header row index for the GL file")
    parser.add_argument("--prev-header", type=int, default=0, help="Header row index for the prior TB file")
    parser.add_argument("--curr-header", type=int, default=0, help="Header row index for the current TB file")

    args = parser.parse_args()

    gl_df = load_gl_for_jet(args.gl, header_row=args.gl_header)
    pre_tb_df = load_tb(args.prev, header_row=args.prev_header)
    cur_tb_df = load_tb(args.curr, header_row=args.curr_header)

    diff_df = perform_roll_forward_test(gl_df, pre_tb_df, cur_tb_df)

    if diff_df.empty:
        print("\N{white heavy check mark} Roll-forward test passed. No differences found.")
    else:
        print("\N{warning sign} Roll-forward differences detected:\n")
        print(diff_df.to_string(index=False))


if __name__ == "__main__":
    main()
