#!/usr/bin/env python3

from shapely.geometry import Point, LineString
import folium
import pandas as pd
from fastkml import kml
from pyproj import Geod
from retrieve_strava_data import get_strava_positions
from create_target import create_target
from project_setup import get_line_start_end
import zipfile
import matplotlib.pyplot as plt
import plotly.express as px
import polyline
from parameters import start_date, target_date, foot_target 

def _point_at_distance_(line, distance):
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

def point_at_distance_lookup(distance, lookup_file = 'distance_lookup.csv'):
    
    df = pd.read_csv(lookup_file)
    if distance>df['Accumalated Distance'].iloc[-1] or distance<0:
        raise ValueError("Distance must be between 0 and the length of the LineString.")
    
    
    index = df[df['Accumalated Distance']>(distance)].index[0]
    
    boundary_rows = df.iloc[index-1: index+1]

    accumulated_distance=boundary_rows['Accumalated Distance'].iloc[0]
    segment_distance = boundary_rows['Segment Distance'].iloc[1]
    segment_fraction = (distance - accumulated_distance) / segment_distance

    p1x = boundary_rows["Point x"].iloc[0]
    p1y = boundary_rows["Point y"].iloc[0]
    p2x = boundary_rows["Point x"].iloc[1]
    p2y = boundary_rows["Point y"].iloc[1]

    x = p1x + segment_fraction * (p2x - p1x)
    y = p1y + segment_fraction * (p2y - p1y)
    return Point(x, y)

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
    current_position = point_at_distance_lookup(current_distance)

    df["Date"] = pd.to_datetime(df["Date"])
    df["Week of Project"] = df["Date"].dt.isocalendar().week - df["Date"][0].week
    weekly_positions = df.groupby('Week of Project')["Distance (km)"].sum().reset_index()
    weekly_positions["weekly_positions"] = weekly_positions["Distance (km)"].cumsum()
    return current_position, weekly_positions[['Week of Project',"weekly_positions"]] 


def create_map(start, end, line, current_position, weekly_positions, target=None):
    mymap = folium.Map(location=(current_position.coords[0][1],current_position.coords[0][0]), zoom_start=6)

    # Add the LineString to the map
    folium.PolyLine(locations=[(coord[1], coord[0]) for coord in line.coords], color='blue').add_to(mymap)
    folium.Marker(location=[start.y, start.x], popup="Start point", icon=folium.Icon(color='darkblue')).add_to(mymap)
    folium.Marker(location=[end.y, end.x], popup="End point", icon=folium.Icon(color='darkblue')).add_to(mymap)

    for i , value in enumerate(weekly_positions["weekly_positions"]):
        pos = point_at_distance_lookup(value)
        folium.Marker(location=[pos.y, pos.x], popup=f"Position after week {weekly_positions['Week of Project'][i]}", icon=folium.Icon(color='purple')).add_to(mymap)
    target_position = point_at_distance_lookup(target)
    folium.Marker(location=[target_position.y, target_position.x], popup=f'Target at end of day: {pd.Timestamp.now().date()}', icon=folium.Icon(color='orange',icon_color='white',icon='warning-sign')).add_to(mymap)
    folium.Marker(location=[current_position.y, current_position.x], popup=f"Position as of {pd.Timestamp.now()}", icon=folium.Icon(color='green')).add_to(mymap)

    mymap.save("Project_san_marino_map.html")

def plot_per_person(df):
    grouped = df.groupby(['User','sport_type'])["distance"].sum().reset_index()
    grouped["Sport Type"] = grouped["sport_type"]
    grouped['Distance'] = grouped['distance']/1000
    fig = px.bar(grouped, x="User", y="Distance", color="Sport Type", title="Distance by Person and Sport",width=300, height=400)
    fig.write_html('Distance_per_person_plot.html')

def plot_worm(df, df_target):
    df_target = df_target.copy()
    df['Activity Date'] = df['start_date'].dt.date
    grouped = df.groupby('Activity Date')['distance'].sum().reset_index()
    grouped['Distance'] = grouped['distance'].cumsum()/1000
    
    fig = px.line(grouped, x='Activity Date', y="Distance", title='Distance Worm',color_discrete_sequence=['blue'], width=600, height=400)
    df_target['Target']=df_target['Target']/1000
    fig.add_trace(px.line(df_target, x='Date', y='Target', title='Target',color_discrete_sequence=['Red']).data[0])
    
    #fig = px.line(target_df, x='Date', y='Target')
    fig.write_html('Distance_worm_plot.html')

def plot_routes_map(df, start):
    df['map.polyline'] = df['map.summary_polyline'].apply(polyline.decode)
    routes_map = folium.Map(location=(start.coords[0][1],start.coords[0][0]), zoom_start=11)
    colors = ['purple', 'red', 'blue', 'green','yellow']
    # Add the LineString to the map
    for i, unique in enumerate(df['User'].unique()):
        df_filtered = df[df['User']==unique]
        for row in df_filtered.iloc(axis=0):
            line = row['map.polyline']
            if line:
                folium.PolyLine(locations=line, color=colors[i], weight=4, opacity=0.4).add_to(routes_map)

    routes_map.save('Routes.html')

def print_targets(foot_target, df, target_df):
    overall_target = target_df['Target'].iloc[-1]
    
    foot_total = df[df['sport_type'].isin(['Run', 'Walk', 'Hike'])]['distance'].sum()
    bike_total = df[df['sport_type'].isin(['Ride'])]['distance'].sum()


    overall_total = df['distance'].sum()

    current_date = pd.Timestamp.now().date()

    date_percentage = float(100*(target_df[target_df['Date'].dt.date==current_date]['Day'])/(target_df['Day'].iloc[-1]))

    print(f'{foot_total/foot_target *100:.1f}% of the way to the foot target')
    print(f'{bike_total/overall_total *100:.1f}% of current distance covered by bike')

    print(f'{overall_total/overall_target *100:.1f}% of the way to the overall target in {date_percentage:.1f}% of total time')
    

def create_html(current_distance, completion_percentage, days_remaining, current_rate, required_rate, days_ahead): 
    with open('dash_template.html') as f:
        s = f.read()
    s= s.replace('{current_distance}', f'{current_distance/1000:.2f} km')
    s= s.replace('{completion_percentage}', f'{completion_percentage:.1f} %')
    s= s.replace('{days_remaining}', f'{days_remaining}')
    s= s.replace('{current_rate}', f'{current_rate:.2f} km/day')
    s= s.replace('{required_rate}', f'{required_rate:.2f} km/day')
    if days_ahead>=0:
        s = s.replace('{days_ahead}', f'{days_ahead} ahead')
    else:
        s = s.replace('{days_ahead}', f'{days_ahead} behind')
    with open('dash.html', 'w') as outfile:
        outfile.write(s)


def calculate_stats(start_date, target_date, current_distance, target_distance, target_df):
    start_date = pd.to_datetime(start_date, format='%d/%m/%Y')
    target_date = pd.to_datetime(target_date, format='%d/%m/%Y')
    current_date = pd.Timestamp.now()
    days_remaining = (target_date-current_date).days

    distance_remaining = target_distance - current_distance
    
    ndays_done = (current_date - start_date).days
    current_rate = (current_distance/ndays_done)/1000
    required_rate = (distance_remaining/days_remaining)/1000

    completion_percentage= current_distance/target_distance *100


    days_ahead = target_df[target_df['Target']>current_distance]['Day'].iloc[0]-ndays_done
    return completion_percentage, days_remaining, current_rate, required_rate, days_ahead

if __name__=='__main__':
    line, start, end = get_line_start_end('Directions_file.kmz')
    lookup_file = "Distance_lookup.csv"
    #current_position, weekly_positions = get_position_data('Distance_tracker.xlsx')
    current_distance, weekly_positions, position_df = get_strava_positions()
    plot_per_person(position_df)
    plot_routes_map(position_df, start)
    #print(position_df.head())
    geod = Geod(ellps='WGS84')
    target_distance = geod.geometry_length(line)

    current_position = point_at_distance_lookup(current_distance, lookup_file)

    current_target, target_df = create_target(start_date, target_date, target_distance)
    
    plot_worm(position_df, target_df)
    print(f"The current total distance is {round(current_distance/1000,2)}km")
    create_map(start, end, line, current_position, weekly_positions, current_target)
    
    print_targets(foot_target, position_df, target_df)
    completion_percentage, days_remaining, current_rate, required_rate,days_ahead = calculate_stats(start_date, target_date, current_distance, target_distance,target_df)

    create_html(current_distance, completion_percentage, days_remaining, current_rate, required_rate, days_ahead)