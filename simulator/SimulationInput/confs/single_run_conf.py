sim_scenario_conf = {

	"requests_rate_factor": 1,
	"n_cars_factor": 1,

	"time_estimation": True,
	"queuing": True,

	"alpha": 40,
	"beta": 100,
	"n_poles_n_cars_factor": 1,

	"hub": False,
	"hub_zone_policy": "",

	"distributed_cps": True,
	"cps_placement_policy": "num_parkings",
	"cps_zones_percentage": 1,
	"system_cps": False,

	"battery_swap": True,
	"avg_reach_time": 30,
	"avg_service_time": 5,

	"n_workers": 1000,
	"relocation": False,

	"user_contribution": False,
	"willingness": 0.5,

}
