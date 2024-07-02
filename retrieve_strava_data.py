import requests
import urllib3
import pandas as pd
from strava_payloads import payloads
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

auth_url = "https://www.strava.com/oauth/token"
activites_url = "https://www.strava.com/api/v3/athlete/activities"


def retrieve_strava_data():

    data = {}
    for person in payloads: 
        
        #print("Requesting Token...\n")
        res = requests.post(auth_url, data=payloads[person], verify=False)
        try:
            access_token = res.json()['access_token']
        except:
            access_token=''
            print(res.json())
            
        #print("Access Token = {}\n".format(access_token))

        header = {'Authorization': 'Bearer ' + access_token}
        param = {'per_page': 200, 'page': 1}
        my_dataset = requests.get(activites_url, headers=header, params=param).json()


        activities = pd.json_normalize(my_dataset)
        activities["User"] = person
        data[person]=activities
        
    return data


def get_strava_positions():
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
    data = retrieve_strava_data()
    for user in data:
        data[user].to_csv(f"Strava_runs_{user}.csv")
