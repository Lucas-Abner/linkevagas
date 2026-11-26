import pandas as pd
from sklearn.model_selection import train_test_split
import numpy as np

def load_and_process_data():
    df = pd.read_csv('dados.csv')
    return df

# Carregando e processando os dados
loaded_df = load_and_process_data()
print(loaded_df.head())