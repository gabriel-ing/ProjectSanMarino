import requests
import urllib3
import pandas as pd

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

auth_url = "https://www.strava.com/oauth/token"
activites_url = "https://www.strava.com/api/v3/athlete/activities"

payload_GI = {
    'client_id': "129255",
    'client_secret': '3681592542e4b0c070643fc43372913f3bd92bf0',
    'refresh_token': '295121019eb432cfce9119e1da31d1784e0d17b2',
    'grant_type': "refresh_token",
    'f': 'json'
}
payload_HQ = {
    'client_id': "129272",
    'client_secret': '52344d101b204f9f48cfeb3a6ba6f3b01988a090',
    'refresh_token': 'faa597b4f3bafaf3e2bdca0cc9fa7235d97dfc48',
    'grant_type': "refresh_token",
    'f': 'json'
}
payload_HQ2 = {
    'client_id': "129295",
    'client_secret': '785ec5b892a62028231343d10a9088487424dae5',
    'refresh_token': '2faf87c2b8d5aa69396cf293e6d1d1bb2d08d5d3',
    'grant_type': "refresh_token",
    'f': 'json'
}
payloads = {'GI':payload_GI, 'HQ':payload_HQ2}
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

if __name__=='__main__':
    data = retrieve_strava_data()
    for user in data:
        data[user].to_csv(f"Strava_runs_{user}.csv")
