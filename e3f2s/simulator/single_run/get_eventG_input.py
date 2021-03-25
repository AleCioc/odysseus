import datetime
from e3f2s.simulator.simulation_input.sim_input import SimInput


def get_eventG_input (conf_tuple):

    simInput = SimInput(conf_tuple)
    simInput.init_vehicles()
    simInput.init_charging_poles()
    simInput.init_relocation()

    print(datetime.datetime.now(), "Simulation input initialised!")
    return simInput