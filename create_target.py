import pandas as pd

def create_target(start_date, target_date, total_distance):
    start_date = pd.to_datetime(start_date, format='%d/%m/%Y')
    target_date = pd.to_datetime(target_date, format='%d/%m/%Y')
    current_date = pd.Timestamp.now()
    print((target_date-start_date).days)


    daily_amount = total_distance/((target_date-start_date).days)

    current_target = ((current_date - start_date).days+1) * daily_amount

    return current_target

if __name__=='__main__':
    start_date = '26/06/2024'
    target_date = '24/08/2024'
    current_target = create_target(start_date, target_date, 2196000)
