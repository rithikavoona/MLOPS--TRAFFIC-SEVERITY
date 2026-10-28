"""Severity model dashboard page."""
import pandas as pd
import plotly.express as px
import streamlit as st
from src.config import SEVERITY, ROAD, WEATHER, LIGHT, SURFACE, AREA
from src.dashboard.charts import chart
from src.dashboard.data import load_model_metrics
from src.dashboard.api_client import PredictionServiceError, predict_severity
from src.dashboard.theme import SEVERITY_COLORS as COLORS
from src.dashboard.context import DashboardContext


def render(context: DashboardContext) -> None:
    metrics = load_model_metrics()
    if metrics is None:
        st.info('Train the model: python -m src.train')
    else:
        st.subheader('Chronological held-out evaluation')
        a, b, c = st.columns(3)
        a.metric('Macro F1', f'{metrics["macro_f1"]:.3f}')
        b.metric('Balanced accuracy', f'{metrics["balanced_accuracy"]:.3f}')
        c.metric('Fatal recall', f'{metrics["report"].get("Fatal", {}).get("recall", 0):.3f}')
        st.caption(f'Train years: {metrics["train_years"]} · Validation: {metrics["validation_year"]} · Test: {metrics["test_year"]} · Model version: {metrics["version"]}')
        chart(px.imshow(metrics['confusion_matrix'], x=list(SEVERITY.values()), y=list(SEVERITY.values()), text_auto=True, labels={'x': 'Predicted', 'y': 'Actual'}, title='Test confusion matrix'))
        st.warning('Research model: severity probabilities describe collisions conditional on a collision occurring. This model does not predict whether a collision will occur, and probabilities are not calibrated.')
        with st.form('prediction'):
            st.subheader('Explore a collision scenario')
            a, b, c = st.columns(3)
            values = {}
            with a:
                values['hour'] = st.slider('Hour', 0, 23, 17)
                values['month'] = st.slider('Month', 1, 12, 6)
                values['weekday_number'] = st.selectbox('Weekday', range(7), format_func=lambda x: ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][x])
                values['speed_limit'] = st.selectbox('Speed limit (mph)', [20, 30, 40, 50, 60, 70], index=1)
            with b:
                for field, label, mapping in [('road_type','Road type',ROAD), ('weather_conditions','Weather',WEATHER), ('light_conditions','Lighting',LIGHT), ('road_surface_conditions','Surface',SURFACE)]:
                    values[field] = st.selectbox(label, list(mapping), format_func=mapping.get)
            with c:
                values['urban_or_rural_area'] = st.selectbox('Area type', list(AREA), format_func=AREA.get)
                values['first_road_class'] = st.selectbox('Road class (DfT code)', [1, 2, 3, 4, 5, 6], index=2)
                values['latitude'] = st.number_input('Latitude', 49.0, 61.0, 51.5)
                values['longitude'] = st.number_input('Longitude', -9.0, 2.5, -0.12)
            submitted = st.form_submit_button('Estimate severity')
        if submitted:
            try:
                with st.spinner('Requesting prediction from the API...'):
                    prediction = predict_severity(values)
            except PredictionServiceError as exc:
                st.error(str(exc))
                return
            st.success(f"Predicted severity: {prediction['severity']}")
            st.caption(f"Prediction served by API · Model version: {prediction['model_version']}")
            results = pd.DataFrame(list(prediction['probabilities'].items()), columns=['Severity', 'Probability'])
            chart(px.bar(results, x='Severity', y='Probability', color='Severity', color_discrete_map=COLORS, range_y=[0,1]))
