import pandas as pd

if __name__ == '__main__':
    df = pd.read_csv('data/raw/email.csv', nrows=5)
    print('COLUMNS:', df.columns.tolist())
    print('\nSAMPLE ROW:')
    print(df.iloc[0].to_dict())
