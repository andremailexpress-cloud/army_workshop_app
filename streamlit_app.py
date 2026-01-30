import streamlit as st
import pandas as pd
import math

# 1. Page Config
st.set_page_config(page_title='GDP dashboard', page_icon=':earth_americas:')

# 2. Data Loading (Fetching from URL)
@st.cache_data
def get_gdp_data():
    DATA_URL = "https://raw.githubusercontent.com/streamlit/datasets/master/gdp_data.csv"
    raw_gdp_df = pd.read_csv(DATA_URL)
    gdp_df = raw_gdp_df.melt(['Country Code'], [str(x) for x in range(1960, 2023)], 'Year', 'GDP')
    gdp_df['Year'] = pd.to_numeric(gdp_df['Year'])
    return gdp_df

gdp_df = get_gdp_data()

# 3. App Title
'# :earth_americas: GDP dashboard'

# 4. Filters
min_v, max_v = int(gdp_df['Year'].min()), int(gdp_df['Year'].max())
from_year, to_year = st.slider('Select Years', min_v, max_v, value=[min_v, max_v])

countries = gdp_df['Country Code'].unique()
selected = st.multiselect('Select Countries', countries, ['DEU', 'FRA', 'GBR', 'BRA', 'MEX', 'JPN'])

# 5. Filtering Data
filtered_df = gdp_df[(gdp_df['Country Code'].isin(selected)) & (gdp_df['Year'] <= to_year) & (from_year <= gdp_df['Year'])]

# 6. Charts
st.header('GDP over time', divider='gray')
st.line_chart(filtered_df, x='Year', y='GDP', color='Country Code')

# 7. Metrics
st.header(f'GDP in {to_year}', divider='gray')
first_year = gdp_df[gdp_df['Year'] == from_year]
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
