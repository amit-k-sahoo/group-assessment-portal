# Group Assessment Portal

Sign in with Google, rate Groups 1–10 on Ideation, Features, Look and feel, Governance and
Presentation (1–5 each), and see the combined results.

Run locally: `pip install -r requirements.txt`, copy `.streamlit/secrets.toml.example` to
`.streamlit/secrets.toml`, then `streamlit run streamlit_app.py`.

Deploy: share.streamlit.io → New app → this repo, `main`, `streamlit_app.py`; paste the secrets
into Advanced settings → Secrets. Ratings are stored in SQLite (`data/ratings.db`), which is
wiped when Streamlit Cloud restarts the app — export the CSV from the Results page first.
