"""FSM states."""
from aiogram.fsm.state import State, StatesGroup


class OrderFlow(StatesGroup):
    choosing_provider = State()
    choosing_location = State()
    choosing_plan = State()
    choosing_image = State()
    entering_hostname = State()
    entering_ssh_key = State()
    choosing_period = State()
    confirming = State()


class SupportFlow(StatesGroup):
    writing_message = State()


class AdminFlow(StatesGroup):
    entering_user_query = State()
    entering_balance_change = State()
