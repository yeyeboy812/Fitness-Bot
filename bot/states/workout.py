"""FSM states for workout-related flows.

The active workout session now uses :class:`bot.states.app.AppState`
(``workout_name_input`` / ``workout_set_input`` / ``workout_in_progress``).
Only the ancillary "create exercise" flow keeps its own StatesGroup.
"""

from aiogram.fsm.state import State, StatesGroup


class CreateExerciseSG(StatesGroup):
    enter_name = State()
    select_muscle_group = State()
    select_type = State()
    confirm = State()
