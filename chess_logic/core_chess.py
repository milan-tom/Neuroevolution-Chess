"""Contains final layer of chess state handling"""

from chess_logic.board import Coord, OPPOSITE_SIDE, PIECE_OF_SIDE, STARTING_FEN
from chess_logic.move_generation import Move, MoveGenerator


class Chess(MoveGenerator):
    """Provides full handling of chess state"""

    def __init__(self, fen: str = STARTING_FEN) -> None:
        super().__init__(fen)
        self.update_board_state()

    def update_board_state(self) -> None:
        """Performs necessary updates when board state changed"""
        self.current_legal_moves = self.legal_moves()

    def legal_moves_from_square(self, square: Coord) -> list[Move]:
        """Returns all legal moves from specific square on board"""
        return [move for move in self.current_legal_moves if move.old_square == square]

    def move_piece(self, move: Move) -> None:
        """Moves piece at given square to new square"""
        if captured_piece := self.get_piece_at_square(move.new_square):
            self.remove_bitboard_square(captured_piece, move.new_square)
        self.move_piece_bitboard_square(
            moved_piece := self.get_piece_at_square(move.old_square),
            move.old_square,
            move.new_square,
        )

        en_passant_bitboard = 0
        match move.context_flag:
            case "PROMOTION":
                self.remove_bitboard_square(
                    PIECE_OF_SIDE[(self.next_side, "P")], move.new_square
                )
                self.add_bitboard_square(move.context_data, move.new_square)
            case "EN PASSANT":
                self.remove_bitboard_square(
                    PIECE_OF_SIDE[(OPPOSITE_SIDE[self.next_side], "P")],
                    move.context_data,
                )
            case "DOUBLE PUSH":
                en_passant_bitboard = move.context_data
            case "CASTLING":
                self.move_piece_bitboard_square(
                    PIECE_OF_SIDE[(self.next_side, "R")], *move.context_data
                )

        self.update_metadata(
            moved_piece, move.old_square, en_passant_bitboard, captured_piece
        )
        self.update_board_state()
