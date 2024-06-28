#!/usr/bin/env python3

from fastkml import kml
import zipfile
from shapely.geometry import Point, LineString, Polygon
import folium
import pandas as pd
from shapely.geometry import LineString
from pyproj import Geod
from retrieve_strava_data import retrieve_strava_data
from create_target import create_target

def point_at_distance(line, distance):
    """
    Calculate the point which is `distance` meters into the `LineString`.

    Parameters:
    - line (LineString): The input LineString.
    - distance (float): The distance in kilometers along the line.

    Returns:
    - Point: The coordinates of the point at the specified distance.
    """
    geod = Geod(ellps='WGS84')
    distance = distance
    if distance <= 0 or distance > geod.geometry_length(line):
        raise ValueError("Distance must be between 0 and the length of the LineString.")

    accumulated_distance = 0.0
    for i in range(len(line.coords) - 1):
        p1 = Point(line.coords[i])
        p2 = Point(line.coords[i+1])

        # Distance between consecutive points
        segment_distance = geod.inv(p1.x, p1.y, p2.x, p2.y)[2]

        if accumulated_distance + segment_distance >= distance:
            # Find the exact point on this segment
            segment_fraction = (distance - accumulated_distance) / segment_distance
            x = p1.x + segment_fraction * (p2.x - p1.x)
            y = p1.y + segment_fraction * (p2.y - p1.y)
            return Point(x, y)

        accumulated_distance += segment_distance

    # If distance is exactly at the end of the LineString
    return Point(line.coords[-1])



def get_line_start_end(kmz_file):
    with zipfile.ZipFile(kmz_file, 'r') as kmz:
        kmz.extractall('.')
    kml_file = f'doc.kml'

    with open(kml_file, 'rb') as file:
        kml_data = file.read()


    k = kml.KML()
    k.from_string(kml_data)
    doc = [feature for feature in k.features()][0]
    line_kmz, start, end = [x.geometry for x in doc.features()]
    line = LineString(line_kmz.coords)
    return line, start, end


def get_position_data(file):
    df = pd.read_excel(file, 'Sheet1')
    current_distance = df["Distance (km)"].sum()
    print(f"Current distance {current_distance}")
    current_position = point_at_distance(line, current_distance)

    df["Date"] = pd.to_datetime(df["Date"])
    df["Week of Project"] = df["Date"].dt.isocalendar().week - df["Date"][0].week
    weekly_positions = df.groupby('Week of Project')["Distance (km)"].sum().reset_index()
    weekly_positions["weekly_positions"] = weekly_positions["Distance (km)"].cumsum()
    return current_position, weekly_positions[['Week of Project',"weekly_positions"]] 


def create_map(start, end, line, current_position, weekly_positions, target=None):
    mymap = folium.Map(location=(start.coords[0][1],start.coords[0][0]), zoom_start=6)

    # Add the LineString to the map
    folium.PolyLine(locations=[(coord[1], coord[0]) for coord in line.coords], color='blue').add_to(mymap)
    folium.Marker(location=[start.y, start.x], popup="Start point", icon=folium.Icon(color='darkblue')).add_to(mymap)
    folium.Marker(location=[end.y, end.x], popup="End point", icon=folium.Icon(color='darkblue')).add_to(mymap)

    for i , value in enumerate(weekly_positions["weekly_positions"]):
        pos = point_at_distance(line, value)
        folium.Marker(location=[pos.y, pos.x], popup=f"Position after week {weekly_positions['Week of Project'][i]}", icon=folium.Icon(color='purple')).add_to(mymap)
    target_position = point_at_distance(line, target)
    folium.Marker(location=[target_position.y, target_position.x], popup=f'Target at end of day: {pd.Timestamp.now().date()}', icon=folium.Icon(color='orange',icon_color='white',icon='warning-sign')).add_to(mymap)
    folium.Marker(location=[current_position.y, current_position.x], popup=f"Position as of {pd.Timestamp.now()}", icon=folium.Icon(color='green')).add_to(mymap)

    mymap.save("Project_san_marino_map.html")

def get_strava_data():
    #files = ["Strava_runs_GI.csv", "Strava_runs_HQ.csv"]
    data = retrieve_strava_data()
    project_dfs = []
    for df in data.values():
        df['start_date'] = pd.to_datetime(df['start_date'])
        project_start_date = pd.to_datetime('26/06/2024', format='%d/%m/%Y').tz_localize('UTC')
        project_df = df[df['start_date']>=project_start_date]
        project_dfs.append(project_df)
    
    project_df = pd.concat(project_dfs)
    #print(project_df.head())

    weekly_positions = get_weekly_data(project_df, project_start_date)
    current_position = project_df["distance"].sum()

    return current_position, weekly_positions, project_df

def get_weekly_data(project_df, project_start_date):
    project_df["Week of Project"] = project_df["start_date"].dt.isocalendar().week - project_start_date.week
    weekly_positions = project_df.groupby('Week of Project')["distance"].sum().reset_index()
    weekly_positions["weekly_positions"] = weekly_positions["distance"].cumsum()
    return weekly_positions

if __name__=='__main__':
    line, start, end = get_line_start_end('Directions_file.kmz')
    #current_position, weekly_positions = get_position_data('Distance_tracker.xlsx')
    current_distance, weekly_positions, position_df = get_strava_data()
    current_position = point_at_distance(line, current_distance)

    start_date = '26/06/2024'
    target_date = '24/08/2024'
    current_target = create_target(start_date, target_date, 2196000)
    print(f"The current total distance is {round(current_distance/1000,2)}km")
    create_map(start, end, line, current_position, weekly_positions, current_target)