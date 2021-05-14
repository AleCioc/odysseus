import os
from datetime import datetime
import random
import pandas as pd
import pymongo as pm
import json

from shapely.geometry import Point, LineString, Polygon
import geopandas as gpd


import skmob
from skmob.tessellation import tilers
from bson import json_util


HOST = 'mongodb://localhost:27017/'
DATABASE = 'inter_test'
COLLECTION = 'test'

def set_path(api):
    ROOT_DIR = os.path.abspath(os.curdir)
    cdm_data_path = os.path.join(
	    ROOT_DIR,
        f"odysseus/{api}/",
	    "data"
    )
    return cdm_data_path


def initialize_mongoDB(host=HOST,database=DATABASE,collection=COLLECTION):
    client = pm.MongoClient(host)
    db = client[database]
    col = db[collection]
    return db,col

def extract_params (body):
    cities = body["cities"]
    years = body["years"]
    months = body["months"]
    data_source_ids = body["data_source_ids"]
    return cities,years,months,data_source_ids

def count_trips(filename):
    with open(filename,"rb") as f:
        return sum(1 for line in f)

def extract_format(filepath):
    source,name = os.path.split(os.path.splitext(filepath)[0])
    _,data_source_id = os.path.split(source)
    names_list = name.split("_")
    if len(names_list)<=2:
        year = names_list[0]
        month = names_list[1]
        return data_source_id,year,month
    else:
        city = "_".join([n for n in names_list[1:]])
        return data_source_id,"",city

def groupby_month(filepath):
    cols = ["init_time"]
    df = pd.read_csv(filepath,usecols=cols)
    df['init_time'] = pd.to_datetime(df['init_time'], unit='s').dt.to_pydatetime()
    df["occurance"] = 1
    df["year"] = df['init_time'].dt.year
    df["month"] = df['init_time'].dt.month
    count_df = df.groupby(["year","month"]).sum(["occurance"])
    ans = build_raw_answer(count_df)
    return ans

def groupby_day_hour(filepath,city):
    cols = ["start_time"]
    df = pd.read_csv(filepath,usecols=cols)
    df['start_time'] = pd.to_datetime(df['start_time'],utc=True).dt.to_pydatetime()
    df["occurance"] = 1
    df["year"] = df['start_time'].dt.year
    df["month"] = df['start_time'].dt.month
    df["day"] = df['start_time'].dt.day
    df["hour"] = df['start_time'].dt.hour
    count_df = df.groupby(["year","month","day","hour"]).sum(["occurance"])
    ans = build_raw_answer_hour(count_df,city)
    return ans

def build_raw_answer(df,DEBUG=False):
    final_dict = {}
    for index, row in df.iterrows():
        if index[0] in final_dict.keys():
            final_dict[index[0]].update({index[1]:int(row["occurance"])})
        else:
            final_dict.update({index[0]:{index[1]:int(row["occurance"])}})
    if DEBUG:
        print(final_dict)
    return final_dict 

def build_raw_answer_hour(df,city,DEBUG=False):
    final_dict = {}
    prev_hour = -1
    prev_day = 0
    for index, row in df.iterrows():
        #index[0] =year
        #index[1] = month
        #index[2] = day
        #index[3] = hour
        print("DAY: ",index)
        if index[0] in final_dict.keys() and index[1] in final_dict[index[0]].keys() and index[2] in final_dict[index[0]][index[1]].keys():
            if index[2]!=1:
                if len(final_dict[index[0]][index[1]][index[2]-1])!=24:
                    print(final_dict[index[0]][index[1]][index[2]-1])
                    a=1/0
            if abs(prev_hour - index[3])> 1 and prev_day==index[2]:
                for _ in range(1, abs(prev_hour - index[3]) ):
                    final_dict[index[0]][index[1]][index[2]].append(0)
            # else:
            #     final_dict[index[0]][index[1]][index[2]].append(int(row["occurance"]))  
            
        elif index[0] in final_dict.keys() and index[1] in final_dict[index[0]].keys() :
            final_dict[index[0]][index[1]].update({index[2]:[]})
            for _ in range(0, abs(23 - prev_hour)):
                final_dict[index[0]][index[1]][prev_day].append(0)
            for gg in range(1, abs(prev_day - index[2]) ):
                michael_jordan_zeros = [0 for x in range(24)]
                final_dict[index[0]][index[1]].update({prev_day+gg:michael_jordan_zeros})
            for _ in range(0,index[3]):
                final_dict[index[0]][index[1]][index[2]].append(0)
            #final_dict[index[0]][index[1]][index[2]].append(int(row["occurance"]))

        elif index[0] in final_dict.keys() :
            final_dict[index[0]].update({index[1]:{index[2]:[]}})
            for _ in range(0,index[3]):
                final_dict[index[0]][index[1]][index[2]].append(0)
            #final_dict[index[0]][index[1]][index[2]].append([int(row["occurance"])])
        else:
            final_dict.update({index[0]:{index[1]:{index[2]:[]}}})
            for _ in range(0,index[3]):
                final_dict[index[0]][index[1]][index[2]].append(0)
        final_dict[index[0]][index[1]][index[2]].append(int(row["occurance"]))
        prev_hour = index[3]
        prev_day = index[2]
    final_dict.update({"city":city})
    db,col = initialize_mongoDB()
    id_object = col.insert_one(json.loads(json_util.dumps(final_dict)))
    return final_dict


def retrieve_per_city(path,level="norm",datatype = "trips",aggregate_level="month",DEBUG=False):
    data = {}
    if DEBUG:
        print("PATH",path)
    for subdir, dirs, files in os.walk(path):
        for f in files:
            filepath = os.path.join(subdir,f)
            if os.path.join(level,datatype,"big_data_db") not in filepath:
                continue

            elif level=="norm" and filepath.endswith(".csv"):
                if DEBUG:
                    print("FILEPATH: ",filepath)
                data_source_id,year,month = extract_format(filepath)
                if aggregate_level =="month":
                    number_trips = count_trips(filepath)
                #if data source already added append to current data structure
                if data_source_id in data.keys():
                    # if year is not already present append dictionary
                    if year not in data[data_source_id].keys():
                        data[data_source_id][year] = {month:number_trips}
                    else:
                        data[data_source_id][year][month] = number_trips
                else:
                    data[data_source_id] = {year : {month:number_trips}}

            elif level=="raw" and filepath.endswith(".csv"):
                if DEBUG:
                    print("FILEPATH: ",filepath)
                data_source_id,_,city = extract_format(filepath)
                if aggregate_level=="month":
                    months_collects = groupby_month(filepath)
                data[data_source_id] = months_collects
    if DEBUG:
        print(data)
    return data

def retrieve_per_city_per_hour(city,path,level="od_trips",datatype = "trips",data_source_id="big_data_db",DEBUG=False):
    data = {}
    if DEBUG:
        print("PATH",path)
    for subdir, dirs, files in os.walk(path):
        for f in files:
            filepath = os.path.join(subdir,f)
            if os.path.join(level,datatype,data_source_id) not in filepath:
                continue

            elif level=="od_trips" and filepath.endswith(".csv"):
                if DEBUG:
                    print("FILEPATH: ",filepath)
                #data_source_id,_,city = extract_format(filepath)
                day_collect = groupby_day_hour(filepath,city)
                data[data_source_id] = day_collect
    if DEBUG:
        print(data)
    return data

def summary_available_data(level='norm',api="city_data_manager",DEBUG=False):
    summary = {}
    # Get list of cities
    path = set_path(api)
    list_subfolders_with_paths = [f.path for f in os.scandir(path) if f.is_dir()]
    avalaible_cities = [os.path.basename(os.path.normpath(c)) for c in list_subfolders_with_paths]
    for paths,city in zip(list_subfolders_with_paths,avalaible_cities):
        data = retrieve_per_city(paths,level=level,DEBUG=DEBUG)
        summary[city] = data
    return summary

def summary_available_data_per_hour(level='od_trips',api="city_data_manager",DEBUG=False):
    summary = {}
    # Get list of cities
    path = set_path(api)
    list_subfolders_with_paths = [f.path for f in os.scandir(path) if f.is_dir()]
    avalaible_cities = [os.path.basename(os.path.normpath(c)) for c in list_subfolders_with_paths]
    for paths,city in zip(list_subfolders_with_paths,avalaible_cities):
        data = retrieve_per_city_per_hour(city,paths,level=level,DEBUG=DEBUG)
        summary[city] = data
    return summary

def create_predefined_file(formato=["norm","raw"],DEBUG=False):
    for f in formato:
        summary = summary_available_data(f,DEBUG=DEBUG)
        filename = os.path.join(
	    os.path.abspath(os.curdir),
        "odysseus","webapp","apis","api_cityDataManager",f"{f}-data.json"
        )
        with open(filename, 'w+') as f:
            json.dump(summary, f) 


def groupby_zone_ods(filepath):    
    cols = ["start_time", "end_time", 'start_longitude', 'start_latitude', 'end_longitude', 'end_latitude']

    df = pd.read_csv(filepath, usecols=cols)
    
    df['start_time'] = pd.to_datetime(df['start_time'],utc=True).dt.to_pydatetime()
    df['end_time'] = pd.to_datetime(df['end_time'],utc=True).dt.to_pydatetime()

    df['year'] = df['end_time'].dt.year
    df['month'] = df['end_time'].dt.month
    df["end_day"] = df['end_time'].dt.day
    df["end_hour"] = df['end_time'].dt.hour

    df['year'] = df['start_time'].dt.year
    df['month'] = df['start_time'].dt.month
    df["start_day"] = df['start_time'].dt.day
    df["start_hour"] = df['start_time'].dt.hour

    origin_df = df[['start_time', 'start_longitude', 'start_latitude']]
    destination_df = df[['end_time', 'end_longitude', 'end_latitude']]
    destination_df['year'] = destination_df['end_time'].dt.year
    destination_df['month'] = destination_df['end_time'].dt.month
    origin_df['year'] = origin_df['start_time'].dt.year
    origin_df['month'] = origin_df['start_time'].dt.month

    
    tessellation = tilers.tiler.get("squared", base_shape="Turin, Italy", meters=500)

    trips_origins = gpd.GeoDataFrame(
        origin_df, geometry=gpd.points_from_xy(origin_df.start_longitude, origin_df.start_latitude))
    trips_origins.crs = "epsg:4326"


    trips_destinations = gpd.GeoDataFrame(
        destination_df, geometry=gpd.points_from_xy(destination_df.end_longitude, destination_df.end_latitude))
    trips_destinations.crs = "epsg:4326"

    tessellation["tile_ID"] = tessellation.index.values

    trips_origins = gpd.sjoin(
        trips_origins,
        tessellation,
        how='left',
        op='intersects'
    )
    trips_destinations = gpd.sjoin(
        trips_destinations,
        tessellation,
        how='left',
        op='intersects'
    )

    df['destination_id'] = trips_destinations.tile_ID
    df['origin_id'] = trips_origins.tile_ID

    # valid zones
    count_threshold=0

    origin_zones_count = df.origin_id.value_counts()
    dest_zones_count = df.destination_id.value_counts()


    valid_origin_zones = origin_zones_count[(origin_zones_count > count_threshold)]
    valid_dest_zones = dest_zones_count[(dest_zones_count > count_threshold)]


    valid_zones = valid_origin_zones.index.intersection(
                    valid_dest_zones.index
            ).astype(int)

    tessellation = tessellation.loc[valid_zones]

    df = df.loc[
                (df.origin_id.isin(valid_zones)) & (
                    df.destination_id.isin(valid_zones)
                )]

    origin_counts = df [['year', 'month', 'start_day', 'start_hour', 'origin_id']]
    origin_counts['occurrance'] = 1
    origin_counts = origin_counts.groupby(
        ['year', 'month', 'start_day', 'start_hour', 'origin_id'], as_index=False
    ).sum(["occurance"])
    
    destination_counts = df [['year', 'month', 'end_day', 'end_hour', 'destination_id']]
    destination_counts['occurrance'] = 1
    destination_counts = destination_counts.groupby(
        ['year', 'month', 'end_day', 'end_hour', 'destination_id'], as_index=False
    ).sum(["occurance"])
    
    return origin_counts, destination_counts


def build_raw_answer_monthly_zone(df, DEBUG=False):

    if all([c in df.columns for c in ['start_day', 'start_hour', 'origin_id']]):
        df = df.drop(['start_day', 'start_hour'], axis=1)
        df = df.groupby(
                ['year', 'month', 'origin_id']
            ).sum(["occurrance"])
        
    elif all([c in df.columns for c in ['end_day', 'end_hour', 'destination_id']]):
        df = df.drop(['end_day', 'end_hour'], axis=1)
        df = df.groupby(
            ['year', 'month', 'destination_id']
        ).sum(["occurance"])
    else:
        print('Errore')
        
    final_dict = {}
    for index, row in df.iterrows():
        value = row['occurrance']
        
        if index[0] in final_dict.keys() and index[1] in final_dict[index[0]].keys() and index[2] in final_dict[index[0]][index[1]].keys():
            final_dict[index[0]][index[1]][index[2]].append(0)
        elif index[0] in final_dict.keys() and index[1] in final_dict[index[0]].keys() :
            final_dict[index[0]][index[1]].update({index[2]:[value]})
        elif index[0] in final_dict.keys() :
            final_dict[index[0]].update({index[1]:{index[2]:[value]}})
        else:
            final_dict.update({index[0]:{index[1]:{index[2]:[value]}}})
            
    return final_dict