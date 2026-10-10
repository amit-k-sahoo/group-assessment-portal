"""Group assessment portal — sign in with a Login ID/password (or Google, if configured), rate Groups 1–10 on five parameters (1–5)."""

import pandas as pd
import streamlit as st

import db

st.set_page_config(page_title="Group Assessment Portal", page_icon="⭐", layout="centered")

LABELS = {1: "1 – Poor", 2: "2 – Fair", 3: "3 – Good", 4: "4 – Very good", 5: "5 – Excellent"}


def admin_settings():
    """[admin] login_id / password from the app's secrets, or None."""
    try:
        cfg = st.secrets["admin"]
        login_id, password = str(cfg["login_id"]).strip(), str(cfg["password"])
    except Exception:
        return None
    return (login_id, password) if login_id and len(password) >= db.MIN_PASSWORD else None


@st.cache_resource
def _seed_admin(login_id: str, password: str):
    db.ensure_admin(login_id, "Portal Admin", password)
    return True


def seed_admin():
    if cfg := admin_settings():
        if not db.user_exists(cfg[0]):  # database was reset (e.g. app restarted)
            _seed_admin.clear()
        _seed_admin(*cfg)


def login_screen():
    st.title("Group Assessment Portal")
    st.write("Assess Groups 1–10 on ideation, features, look and feel, governance and presentation.")
    tab_in, tab_up = st.tabs(["Sign in", "Create account"])
    with tab_in:
        with st.form("login"):
            login_id = st.text_input("Login ID", autocomplete="username")
            password = st.text_input("Password", type="password", autocomplete="current-password")
            if st.form_submit_button("Sign in", type="primary", width="stretch"):
                try:
                    st.session_state["user"] = db.authenticate(login_id, password)
                except db.AuthError as exc:
                    st.error(str(exc))
                else:
                    st.rerun()
    with tab_up:
        with st.form("signup"):
            full_name = st.text_input("Full name", autocomplete="name")
            login_id = st.text_input("Choose a Login ID", key="su_id", autocomplete="username",
                                     help="Your email or any short ID you'll remember.")
            pw1 = st.text_input(f"Password (at least {db.MIN_PASSWORD} characters)", type="password",
                                key="su_pw1", autocomplete="new-password")
            pw2 = st.text_input("Confirm password", type="password", key="su_pw2",
                                autocomplete="new-password")
            if st.form_submit_button("Create account", type="primary", width="stretch"):
                if pw1 != pw2:
                    st.error("Passwords don't match.")
                else:
                    try:
                        st.session_state["user"] = db.create_user(login_id, full_name, pw1)
                    except db.AuthError as exc:
                        st.error(str(exc))
                    else:
                        st.rerun()
    if not auth_config_problems():  # Google sign-in is optional; shown only when configured
        st.divider()
        if st.button("Or sign in with Google", icon=":material/login:"):
            try:
                named = "google" in st.secrets["auth"]
            except Exception:
                named = False
            st.login("google") if named else st.login()


def current_user():
    """Password-account user from the session, else the Google user, else None."""
    if user := st.session_state.get("user"):
        return user["id"], user["name"], False
    try:
        if st.user.get("is_logged_in", False):
            email = (st.user.get("email") or "").lower()
            return email, st.user.get("name") or email, True
    except Exception:
        pass
    return None


def sign_out(google: bool):
    st.session_state.pop("user", None)
    if google:
        st.logout()


def auth_config_problems() -> list:
    """Names (never values) of missing or placeholder auth secrets."""
    try:
        auth = dict(st.secrets["auth"])
    except Exception:
        return ["There is no [auth] section."]
    if isinstance(auth.get("google"), dict) or hasattr(auth.get("google"), "get"):
        auth = dict(auth["google"]) | {k: v for k, v in auth.items() if k != "google"}
    out = []
    for key in ("redirect_uri", "cookie_secret", "client_id", "client_secret", "server_metadata_url"):
        val = str(auth.get(key, "")).strip()
        if not val:
            out.append(f"`{key}` is missing")
        elif val.lower().startswith("xxxx") or "your-app" in val or "<" in val:
            out.append(f"`{key}` is still a placeholder")
    uri = str(auth.get("redirect_uri", ""))
    if uri and not uri.endswith("/oauth2callback"):
        out.append("`redirect_uri` must end with `/oauth2callback`")
    if uri.endswith("/"):
        out.append("`redirect_uri` must not end with a slash")
    return out


def rate_tab(email: str, name: str):
    done = db.rated_groups(email)
    group = st.selectbox(
        "Group to assess", db.GROUPS,
        format_func=lambda g: f"Group {g}" + (" ✓" if g in done else ""),
    )
    st.caption(f"You have completed {len(done)} of {len(db.GROUPS)} groups. "
               "Re-submitting a group replaces your earlier scores.")
    prior = db.my_scores(email, group)
    with st.form(f"rate_{group}"):
        scores = {}
        for key, label in db.PARAMETERS.items():
            scores[key] = st.select_slider(
                label, options=[1, 2, 3, 4, 5], value=prior.get(key, 3),
                format_func=LABELS.get, key=f"{group}_{key}",
            )
        if st.form_submit_button(f"Submit ratings for Group {group}", type="primary"):
            db.save_scores(email, name, group, scores)
            st.success(f"Saved your ratings for Group {group}.")
            st.rerun()


def mine_tab(email: str):
    rows = [r for r in db.all_ratings() if r[0] == email]
    if not rows:
        st.info("You haven't rated any group yet.")
        return
    df = pd.DataFrame(rows, columns=["email", "name", "group", "parameter", "score", "updated"])
    pivot = df.pivot(index="group", columns="parameter", values="score").reindex(columns=list(db.PARAMETERS))
    pivot.columns = [db.PARAMETERS[c] for c in pivot.columns]
    pivot.index = [f"Group {g}" for g in pivot.index]
    st.dataframe(pivot, width="stretch")


def results_tab(is_admin: bool):
    rows = db.all_ratings()
    if not rows:
        st.info("No ratings yet.")
        return
    df = pd.DataFrame(rows, columns=["email", "name", "group", "parameter", "score", "updated"])
    cols = list(db.PARAMETERS)
    avg = df.pivot_table(index="group", columns="parameter", values="score", aggfunc="mean") \
            .reindex(index=db.GROUPS, columns=cols)
    avg["overall"] = avg.mean(axis=1)
    avg["reviewers"] = df.groupby("group")["email"].nunique().reindex(db.GROUPS).fillna(0).astype(int)
    avg = avg.sort_values("overall", ascending=False, na_position="last")

    c1, c2 = st.columns(2)
    c1.metric("Reviewers", df["email"].nunique())
    if avg["overall"].notna().any():
        c2.metric("Top group", f"Group {avg['overall'].idxmax()}", f"{avg['overall'].max():.2f} / 5")

    st.subheader("Ranking")
    table = avg.rename(columns={**db.PARAMETERS, "overall": "Overall", "reviewers": "Reviewers"})
    table.index = [f"Group {g}" for g in table.index]
    cfg = {c: st.column_config.ProgressColumn(c, min_value=0, max_value=5, format="%.2f")
           for c in [*db.PARAMETERS.values(), "Overall"]}
    st.dataframe(table, column_config=cfg, width="stretch")
    st.subheader("Average by parameter")
    chart = avg[cols].rename(columns=db.PARAMETERS)
    chart.index = [f"Group {g}" for g in chart.index]
    st.bar_chart(chart)

    if is_admin:
        st.subheader("Admin")
        st.download_button("Download every individual rating (CSV)", df.to_csv(index=False),
                           "ratings.csv", "text/csv")


def main():
    seed_admin()
    who = current_user()
    if who is None:
        login_screen()
        return
    email, name, google = who
    with st.sidebar:
        st.write(f"Signed in as **{name}**")
        st.caption(email)
        st.button("Sign out", on_click=sign_out, args=(google,))

    is_admin = (not google) and db.is_admin(email)  # role is re-read from the database every run
    st.title("Group Assessment Portal" + (" — Admin" if is_admin else ""))
    if is_admin:
        results_tab(True)
        return
    tabs = st.tabs(["Rate a group", "My ratings"])
    with tabs[0]:
        rate_tab(email, name)
    with tabs[1]:
        mine_tab(email)


main()
