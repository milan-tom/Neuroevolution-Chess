"""Contains any useful constants and functions needed by multiple tests"""

from chess_logic.board import STARTING_FEN

RANDOM_FENS = (
    "1r6/2R1k1pp/3bp3/5p2/4n3/BP2P3/3N1PPP/6K1 b - - 3 24",
    "r4rk1/pp2qppp/4n3/1p6/8/1Q6/PP3PPP/R1B1R1K1 w - - 0 18",
    "r5k1/1p3p1p/p1p2n2/3p1P1n/6pP/4P1q1/PPB3P1/2R1QRK1 b - - 3 27",
    "r1bq1rk1/pppnbppp/4pn2/3p2B1/2PP4/2N1PN2/PP3PPP/2RQKB1R b K - 4 7",
    "r1q1nrk1/1pp2ppp/2nb4/p2Np3/4P1b1/2P1BNP1/PP2QPBP/R2R2K1 w - - 10 16",
    "rnbqk2r/ppp1bppp/4pn2/3p4/8/3P1NP1/PPP1PPBP/RNBQ1RK1 b kq - 0 5",
    "r1bq1rk1/pp3ppp/2nb1n2/1B1p4/3P4/2N2N2/PP3PPP/R1BQ1RK1 w - - 3 10",
    "r5k1/bpR2pp1/p6p/P2P4/1P1N4/3n1NPP/4rP1K/R7 b - - 2 24",
    "r1bqk2r/1pp1bppp/2n2n2/p3p3/2PP4/3P1NP1/PP3PBP/RNBQ1RK1 b kq - 0 8",
)
TEST_FENS = (STARTING_FEN,) + RANDOM_FENS

CHECKMATE_IN_TWO_FENS = {
    "7r/pQ2b2k/8/4NbBK/2P1n3/4P2P/P4rP1/5B1R b - - 2 34": (
        ((1, 7), (1, 6)),
        ((3, 6), (2, 7)),
        ((0, 7), (2, 7)),
    ),
    "5k2/pb1p2p1/5p1B/1p6/3PR3/P7/5q1P/3K1Nr1 b - - 5 32": (
        ((7, 6), (7, 5)),
        ((4, 4), (7, 4)),
        ((7, 5), (7, 4)),
    ),
    "1Q6/5pk1/2p3p1/1p2N2p/1b5P/1b6/r3n1P1/1K6 b - - 13 40": (
        ((6, 4), (5, 2)),
        ((7, 1), (7, 2)),
        ((6, 0), (6, 2)),
    ),
    "8/5pk1/7p/8/1p4P1/1P1R2P1/5qBP/3NrN1K b - - 2 41": (
        ((7, 4), (7, 5)),
        ((6, 6), (7, 5)),
        ((6, 5), (7, 5)),
    ),
    "8/pb1pk1p1/5p2/1p6/3Pq3/P3B3/6rP/4K3 b - - 1 32": (
        ((4, 4), (5, 4)),
        ((7, 4), (7, 3)),
        ((5, 4), (6, 3)),
    ),
}
