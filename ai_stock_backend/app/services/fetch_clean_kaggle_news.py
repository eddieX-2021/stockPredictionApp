import panda as pd

df = pd.read_csv('Combined_News_DJIA.csv')

df.fillna('', inplace=True)

