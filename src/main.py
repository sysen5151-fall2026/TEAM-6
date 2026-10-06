"""Run the UC.1 walking skeleton:  python -m src.main

Prints what the Commuter sees for one stubbed end-to-end pass of
UC.1 'Review Commute Impact and Feasible Alternative'.
"""

from src.x1_commuter_sim import run_uc1

if __name__ == "__main__":
    print(run_uc1())
