"""Configuration file for unit testing via pytest"""

import pytest

from chess_ai.mcts import MCTS
from chess_gui.gui import ChessGUI, Design
from chess_logic.core_chess import Chess


def test_instance_creator(__name, __obj):
    """Returns specific instance of given class usable for specific test"""

    @pytest.fixture(name=__name)
    def fixture(request):
        params = getattr(request, "param", ())
        return __obj(*(params if isinstance(params, tuple) else (params,)))

    return fixture


chess = test_instance_creator("chess", Chess)
design = test_instance_creator("design", Design)
gui = test_instance_creator("gui", ChessGUI)
mcts = test_instance_creator("mcts", MCTS)
