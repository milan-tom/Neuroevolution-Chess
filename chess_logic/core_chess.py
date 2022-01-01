"""Contains final layer of chess state handling"""
from __future__ import annotations
from typing import Any, NamedTuple, Optional

from chess_logic.board import (
    Bitboard,
    CastlingRights,
    Coord,
    OPPOSITE_SIDE,
    STARTING_FEN,
)
from chess_logic.move_generation import Move, MoveGenerator, PIECE_OF_SIDE


class PerformedMove(NamedTuple):
    """Stores sufficient information about performed move to make it revertible"""

    old_square: Coord
    new_square: Coord
    context_flag: Optional[str]
    context_data: Any
    captured_piece: Optional[str]
    old_legal_moves: tuple[Move]
    old_half_move_clock: int
    old_en_passant_bitboard: Bitboard
    castling_rights_lost: CastlingRights


class Chess(MoveGenerator):
    """Provides full handling of chess state"""

    def __init__(self, fen: str = STARTING_FEN) -> None:
        super().__init__(fen)
        self.game_over = False
        self.winner = self.game_over_message = None
        self.update_board_state()

    def update_board_state(self, legal_moves=None) -> None:
        """Performs necessary updates when board state changed"""
        self.current_legal_moves = (
            legal_moves if legal_moves is not None else self.legal_moves()
        )
        self.game_over = True
        if not self.current_legal_moves:
            if self.is_check:
                self.is_checkmate = True
                self.winner = OPPOSITE_SIDE[self.next_side]
                self.game_over_message = f"{self.winner.title()} wins by checkmate"
            else:
                self.is_stalemate = True
                self.game_over_message = "Draw by stalemate"
        elif self.half_move_clock >= 100:
            self.fifty_move_rule_reached = True
            self.game_over_message = "Draw by fifty move rule"
            self.current_legal_moves = []
        else:
            self.game_over = False

    def legal_moves_from_square(self, square: Coord) -> list[Move]:
        """Returns all legal moves from specific square on board"""
        return [move for move in self.current_legal_moves if move.old_square == square]

    def move_piece(self, move: Move) -> Chess:
        """Moves piece at given square to new square, returning new chess state"""
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
                    PIECE_OF_SIDE[self.next_side]["P"], move.new_square
                )
                self.add_bitboard_square(move.context_data, move.new_square)
            case "EN PASSANT":
                self.remove_bitboard_square(
                    PIECE_OF_SIDE[OPPOSITE_SIDE[self.next_side]]["P"],
                    move.context_data[1],
                )
            case "DOUBLE PUSH":
                en_passant_bitboard = move.context_data
            case "CASTLING":
                self.move_piece_bitboard_square(
                    PIECE_OF_SIDE[self.next_side]["R"], *move.context_data
                )

        old_legal_moves = self.current_legal_moves
        old_half_move_clock = self.half_move_clock
        old_en_passant_bitboard = self.en_passant_bitboard
        castling_rights_lost = self.update_metadata(
            *move[:2], en_passant_bitboard, moved_piece, captured_piece
        )
        self.update_board_state()
        return PerformedMove(
            *move,
            captured_piece,
            old_legal_moves,
            old_half_move_clock,
            old_en_passant_bitboard,
            castling_rights_lost,
        )

    def undo_move(self, performed_move: PerformedMove) -> None:
        """Reverts chess state back to what it was before move"""
        self.undo_metadata_update(*performed_move[-3:])
        self.move_piece_bitboard_square(
            self.get_piece_at_square(performed_move.new_square),
            performed_move.new_square,
            performed_move.old_square,
        )
        if (captured_piece := performed_move.captured_piece) is not None:
            self.add_bitboard_square(captured_piece, performed_move.new_square)

        match performed_move.context_flag:
            case "PROMOTION":
                self.remove_bitboard_square(
                    performed_move.context_data, performed_move.old_square
                )
                self.add_bitboard_square(
                    PIECE_OF_SIDE[self.next_side]["P"], performed_move.old_square
                )
            case "EN PASSANT":
                self.add_bitboard_square(
                    PIECE_OF_SIDE[OPPOSITE_SIDE[self.next_side]]["P"],
                    performed_move.context_data[1],
                )
            case "CASTLING":
                self.move_piece_bitboard_square(
                    PIECE_OF_SIDE[self.next_side]["R"],
                    *reversed(performed_move.context_data),
                )

        self.update_board_state(performed_move.old_legal_moves)
