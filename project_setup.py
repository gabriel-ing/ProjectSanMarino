import pandas as pd
from fastkml import kml
import pandas as pd
from shapely.geometry import Point, LineString
from pyproj import Geod
import zipfile

def create_distance_lookup(line):
    geod = Geod(ellps='WGS84')
    accumulated_distance = 0.0
    distances = []
    for i in range(len(line.coords) - 1):
        p1 = Point(line.coords[i])
        p2 = Point(line.coords[i+1])
        segment_distance = geod.inv(p1.x, p1.y, p2.x, p2.y)[2]
        distances.append([p2.x, p2.y, segment_distance])
    df = pd.DataFrame(distances, columns=['Point x', 'Point y', 'Segment Distance']
                                          )
    df['Accumalated Distance'] = df['Segment Distance'].cumsum()
    df.to_csv("Distance_lookup.csv", index=False)
    
def make_kml_file(kmz_file):    
    with zipfile.ZipFile(kmz_file, 'r') as kmz:
        kmz.extractall('.')
    

def get_line_start_end(kml_file='doc.kml'):
    with open(kml_file, 'rb') as file:
        kml_data = file.read()
    k = kml.KML()
    k.from_string(kml_data)
    doc = [feature for feature in k.features()][0]
    line_kmz, start, end = [x.geometry for x in doc.features()]
    line = LineString(line_kmz.coords)
    return line, start, end




if __name__=='__main__':
    kmz_file = 'Directions_file.kmz'
    make_kml_file(kmz_file)
    line, start, end = get_line_start_end()
    create_distance_lookup(line)