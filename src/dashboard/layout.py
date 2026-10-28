"""Header and collision summary components shared above the pages."""
import pandas as pd
import streamlit as st


def render_header() -> None:
    st.caption('ROADSCOPE / GREAT BRITAIN / REPORTED INJURY COLLISIONS')
    st.title('Traffic severity intelligence')
    st.write('Explore when, where and under which recorded conditions injury collisions occur.')


def render_summary(filtered: pd.DataFrame, total_rows: int) -> None:
    st.caption(
        f'{len(filtered):,} of {total_rows:,} cleaned collisions · '
        f'{filtered.date.min():%d %b %Y} – {filtered.date.max():%d %b %Y}'
    )
    collisions, casualties, fatal, severe = st.columns(4)
    collisions.metric('Collisions', f'{len(filtered):,}')
    casualties.metric('Recorded casualties', f'{int(filtered.number_of_casualties.sum()):,}')
    fatal.metric('Fatal collisions', f'{int(filtered.severity.eq("Fatal").sum()):,}')
    severe.metric('Fatal + serious share', f'{filtered.is_severe.mean():.1%}')
