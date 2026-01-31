import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title='GDP Dashboard', page_icon=':earth_americas:')

@st.cache_data
def get_gdp_data():
    # Using the most reliable raw link available
    URL = "https://raw.githubusercontent.com/streamlit/gdp-dashboard-template/master/data/gdp_data.csv"
    try:
        raw_gdp_df = pd.read_csv(URL)
    except:
        # Emergency backup link
        raw_gdp_df = pd.read_csv("https://raw.githubusercontent.com/dataprotocols/datasets/master/data/gdp.csv")
    
    gdp_df = raw_gdp_df.melt(['Country Code'], [str(x) for x in range(1960, 2023)], 'Year', 'GDP')
    gdp_df['Year'] = pd.to_numeric(gdp_df['Year'])
    return gdp_df

gdp_df = get_gdp_data()

'# :earth_americas: GDP Dashboard'

min_v, max_v = int(gdp_df['Year'].min()), int(gdp_df['Year'].max())
from_year, to_year = st.slider('Select Years', min_v, max_v, value=[min_v, max_v])

countries = gdp_df['Country Code'].unique()
selected = st.multiselect('Select Countries', countries, ['DEU', 'FRA', 'GBR', 'BRA', 'MEX', 'JPN'])

filtered_df = gdp_df[(gdp_df['Country Code'].isin(selected)) & (gdp_df['Year'] <= to_year) & (from_year <= gdp_df['Year'])]

st.header('GDP over time', divider='gray')
st.line_chart(filtered_df, x='Year', y='GDP', color='Country Code')

st.header(f'GDP in {to_year}', divider='gray')
last_year = gdp_df[gdp_df['Year'] == to_year]

cols = st.columns(2)
for i, country in enumerate(selected):
    col = cols[i % 2]
    with col:
        try:
            val_last = last_year[last_year['Country Code'] == country]['GDP'].iat[0] / 1e9
            st.metric(label=f'{country} GDP', value=f'${val_last:,.0f}B')
        except:
            pass
