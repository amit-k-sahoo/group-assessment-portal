"""Scoring guide shown under the rating form (static text)."""

import streamlit as st

PARAMETER_GUIDE = [
    ("Ideation",
     "How good the idea is: how real the problem is, how original and valuable the solution, and how well it is thought through.",
     ["Clear problem statement and a real, specific user",
      "Originality: a fresh approach rather than the obvious one",
      "Value and impact: who benefits, and by how much",
      "Feasibility: could it work in practice with the resources available",
      "Fit with the challenge theme"]),
    ("Features",
     "What the solution actually does and how well it works.",
     ["Core functionality works end to end",
      "Depth and completeness: the main use cases are covered",
      "Smart or technical content: models, automation, integrations, data use",
      "Reliability: no crashes or broken flows during the demo",
      "Right scope: useful features, not a long list of half-built ones"]),
    ("Look and feel",
     "The user experience and visual design.",
     ["Clear, intuitive navigation; a new user can start without help",
      "Visual consistency: layout, colours, fonts, spacing",
      "Readability and accessibility: contrast, text size, simple language",
      "Works on different screen sizes",
      "Helpful feedback; clean handling of errors and empty states"]),
    ("Governance",
     "Whether the solution is responsible, safe and accountable. Most relevant for AI and data-driven projects.",
     ["Privacy and data protection: minimal data, consent, access control",
      "Fairness and bias: awareness of who could be harmed or excluded",
      "Transparency: explanations for outputs; honest labelling of synthetic or uncertain data",
      "Human oversight: people stay in the loop for important decisions",
      "Accountability: audit trail, roles and permissions, handling of errors and misuse"]),
    ("Presentation",
     "How well the team communicated the work.",
     ["Clear story: problem, solution, demo, impact",
      "Clarity of speaking and slides; a confident live demo",
      "Good use of time: no rushing, no overrun",
      "Handling of questions: honest, knowledgeable answers",
      "Team coordination: everyone contributes"]),
]

SCORE_GUIDE = [
    ("1: Poor", "Missing or seriously weak", "Little or nothing evidenced in this area"),
    ("2: Fair", "Below expectations", "Attempted, but major gaps"),
    ("3: Good", "Meets expectations", "Solid and competent; typical of a good project with some gaps"),
    ("4: Very good", "Above expectations", "Strong, with only minor weaknesses"),
    ("5: Excellent", "Outstanding", "Hard to improve; reserve for the best examples you have seen"),
]


def render():
    st.divider()
    st.subheader("How to rate: what each parameter means")
    rows = "".join(
        f"<tr><td><b>{name}</b></td><td>{definition}</td><td>{'<br>'.join('• ' + a for a in areas)}</td></tr>"
        for name, definition, areas in PARAMETER_GUIDE
    )
    st.markdown(
        "<table><thead><tr><th>Parameter</th><th>What you are judging</th><th>Areas to assess</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>",
        unsafe_allow_html=True,  # static text defined above; no user input
    )
    st.subheader("How to score: the 1 to 5 scale")
    rows = "".join(f"<tr><td><b>{s}</b></td><td>{m}</td><td>{r}</td></tr>" for s, m, r in SCORE_GUIDE)
    st.markdown(
        "<table><thead><tr><th>Score</th><th>Meaning</th><th>Rule of thumb</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>",
        unsafe_allow_html=True,
    )
    st.caption("Judge each parameter on its own, so a great demo doesn't lift the Governance score. "
               "Score what you saw, not what the team says they will do later.")
