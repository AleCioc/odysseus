import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString

from odysseus.city_data_manager.city_data_source.trips_data_source.norfolk_scooter_trips import NorfolkScooterTrips
from odysseus.city_data_manager.city_data_source.geo_data_source.norfolk_census_tracts import NorfolkCensusTracts
from odysseus.city_data_manager.city_geo_trips.city_geo_trips import CityGeoTrips
from odysseus.utils.geospatial_utils import get_random_point_from_shape

class NorfolkGeoTrips(CityGeoTrips):

    def __init__(self, city_name="Norfolk", trips_data_source_id="city_open_data", year=2019, month=8):

        self.city_name = city_name
        super().__init__(self.city_name, trips_data_source_id, year, month)
        self.trips_ds_dict = {
            "city_open_data": NorfolkScooterTrips()
        }
        self.trips_df_norm = pd.DataFrame()

        self.census_tracts_ds = NorfolkCensusTracts()
        self.census_tracts_ds.load_raw()
        self.census_tracts_ds.normalise()
        self.census_tracts_gdf_norm = self.census_tracts_ds.gdf_norm

    def get_trips_od_gdfs(self):

        self.trips_ds_dict[self.trips_data_source_id].load_raw()
        self.trips_ds_dict[self.trips_data_source_id].normalise(self.year, self.month)

        self.trips_df_norm = self.trips_ds_dict[self.trips_data_source_id].load_norm(
            self.year, self.month
        )
        self.trips_df_norm["trip_id"] = self.trips_df_norm.index

        self.trips_origins = gpd.GeoDataFrame(pd.merge(
            self.trips_df_norm,
            self.census_tracts_gdf_norm,
            left_on="start_census_tract", right_on="census_tract_id"
        ))
        self.trips_origins.geometry = self.trips_origins.geometry.apply(
            get_random_point_from_shape
        )
        self.trips_origins.crs = "epsg:4326"

        self.trips_destinations = gpd.GeoDataFrame(pd.merge(
            self.trips_df_norm,
            self.census_tracts_gdf_norm,
            left_on="end_census_tract", right_on="census_tract_id"
        ))
        self.trips_destinations.geometry = self.trips_destinations.geometry.apply(
            get_random_point_from_shape
        )
        self.trips_origins.crs = "epsg:4326"

        self.trips = pd.merge(
            self.trips_df_norm,
            self.trips_origins[["trip_id", "geometry"]],
            on="trip_id"
        )
        self.trips = self.trips.rename(columns={"geometry": "origin_point"})

        self.trips = pd.merge(
            self.trips,
            self.trips_destinations[["trip_id", "geometry"]],
            on="trip_id"
        )
        self.trips = self.trips.rename(columns={"geometry": "destination_point"})

        self.trips[["start_latitude",
                    "start_longitude",
                    "end_latitude",
                    "end_longitude",
                    "geometry"]] = self.trips.apply(
            lambda row: [row["origin_point"].y,
                         row["origin_point"].x,
                         row["destination_point"].y,
                         row["destination_point"].x,
                         LineString([row["origin_point"], row["destination_point"]])],
            axis=1, result_type="expand"
        )

        self.trips = self.trips.drop(["origin_point", "destination_point"], axis=1)
        self.trips = gpd.GeoDataFrame(self.trips)
        self.trips.crs = "epsg:4326"
