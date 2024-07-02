import pandas as pd
from parameters import start_date, target_date, foot_target 

def create_target(start_date, target_date, total_distance):
    start_date = pd.to_datetime(start_date, format='%d/%m/%Y')
    target_date = pd.to_datetime(target_date, format='%d/%m/%Y')
    current_date = pd.Timestamp.now()
    ndays = (target_date-start_date).days
    print((target_date-start_date).days)


    daily_amount = total_distance/((target_date-start_date).days)

    current_target = ((current_date - start_date).days+1) * daily_amount

    day_range = range(0, ndays)
    target_range = [(x+1)*daily_amount for x in day_range] 
    target_df = pd.DataFrame({"Day":day_range, "Target":target_range})
    
    target_df['Date'] = start_date+pd.to_timedelta(target_df['Day'], unit='D')

    return current_target, target_df

if __name__=='__main__':
    current_target, target_df = create_target(start_date, target_date, 2196000)
