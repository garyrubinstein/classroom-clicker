import streamlit as st
import pandas as pd
import numpy as np
import random

# Set page config for a wide dashboard layout
st.set_page_config(page_title="Real-Time Numeric Clicker Dashboard", layout="wide")

# ---------------------------------------------------------
# CSS Injection for Rule #3: Custom Rainbow Flash Animation
# ---------------------------------------------------------
st.markdown("""
<style>
@keyframes rainbow-flash {
    0% { background-color: #ff0000; box-shadow: 0 0 10px #ff0000; }
    17% { background-color: #ff8800; box-shadow: 0 0 10px #ff8800; }
    33% { background-color: #ffff00; box-shadow: 0 0 10px #ffff00; }
    50% { background-color: #00ff00; box-shadow: 0 0 10px #00ff00; }
    67% { background-color: #0000ff; box-shadow: 0 0 10px #0000ff; }
    83% { background-color: #8b00ff; box-shadow: 0 0 10px #8b00ff; }
    100% { background-color: #ff0000; box-shadow: 0 0 10px #ff0000; }
}

.rainbow-dot {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: inline-block;
    margin: 4px;
    animation: rainbow-flash 3s linear infinite;
    text-align: center;
    line-height: 28px;
    color: white;
    font-size: 10px;
    font-weight: bold;
    cursor: pointer;
}

.normal-dot {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: inline-block;
    margin: 4px;
    text-align: center;
    line-height: 28px;
    color: white;
    font-size: 10px;
    font-weight: bold;
}
</style>
""", unsafe_with_html=True)

# ---------------------------------------------------------
# State Initialization (Dynamic Answer Key & Student Submissions)
# ---------------------------------------------------------
if "answer_key" not in st.session_state:
    st.session_state.answer_key = {
        "Q1": 42.0,
        "Q2": 7.5,
        "Q3": 100.0,
        "Q4": 0.25,
        "Q5": 13.0
    }

if "responses" not in st.session_state:
    st.session_state.responses = []

TOTAL_QUESTIONS = len(st.session_state.answer_key)

# ---------------------------------------------------------
# Sidebar Simulator (Teacher Rules + Student Inputs)
# ---------------------------------------------------------
st.sidebar.title("⚙️ Control Panel & Simulator")

# Section A: Teacher Answer Key Configuration
with st.sidebar.expander("🔑 Edit Teacher Answer Key", expanded=False):
    st.write("Set the correct numeric values for the live session:")
    for q in sorted(st.session_state.answer_key.keys()):
        st.session_state.answer_key[q] = st.sidebar.number_input(
            f"Correct Answer for {q}", 
            value=float(st.session_state.answer_key[q]),
            key=f"key_{q}"
        )

# Section B: Student Phone Simulator
st.sidebar.markdown("---")
st.sidebar.subheader("📱 Student Phone Simulator")

sim_name = st.sidebar.text_input("Student Name", value="Zack")
sim_q = st.sidebar.selectbox("Select Question", options=sorted(list(st.session_state.answer_key.keys())))
sim_ans = st.sidebar.number_input("Student Numeric Answer", value=0.0, step=0.1)

if st.sidebar.button("Submit Answer"):
    is_correct = np.isclose(sim_ans, st.session_state.answer_key[sim_q]) 
    
    st.session_state.responses = [
        r for r in st.session_state.responses 
        if not (r["student"] == sim_name and r["question"] == sim_q)
    ]
    
    st.session_state.responses.append({
        "student": sim_name,
        "question": sim_q,
        "answer": sim_ans,
        "is_correct": bool(is_correct)
    })
    st.toast(f"Submitted {sim_name} -> {sim_q}: {sim_ans}")

if st.sidebar.button("Clear Dashboard Data"):
    st.session_state.responses = []
    st.rerun()

if st.sidebar.button("Load Mock Numeric Class Data"):
    mock_students = ["Ada", "Bernie", "Cole", "Danica", "Eli"]
    st.session_state.responses = []
    for student in mock_students:
        perfect_score = (student in ["Ada", "Eli"])
        for q, correct_val in st.session_state.answer_key.items():
            if perfect_score:
                ans = correct_val
            else:
                ans = correct_val + float(random.choice([0, -2.0, 5.5, 0]))
            st.session_state.responses.append({
                "student": student,
                "question": q,
                "answer": ans,
                "is_correct": bool(np.isclose(ans, correct_val))
            })
    st.rerun()

# ---------------------------------------------------------
# Main Teacher Dashboard Layout
# ---------------------------------------------------------
st.title("🎯 Real-Time Clicker Teacher Dashboard (Numeric Edition)")
st.markdown("---")

if not st.session_state.responses:
    st.info("Waiting for numeric student responses... Submit answers from the sidebar simulator!")
else:
    df = pd.DataFrame(st.session_state.responses)
    
    student_stats = df.groupby("student").agg(
        correct_count=("is_correct", "sum"),
        total_answered=("question", "nunique")
    ).reset_index()
    
    student_stats["accuracy"] = student_stats["correct_count"] / TOTAL_QUESTIONS
    student_stats["is_perfect"] = student_stats["accuracy"] == 1.0

    df = df.merge(student_stats[["student", "is_perfect"]], on="student", how="left")

    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader("🗺️ Student Progress Map")
        
        sorted_questions = sorted(list(st.session_state.answer_key.keys()))
        grid_cols = st.columns(len(sorted_questions))

        for idx, q_num in enumerate(sorted_questions):
            with grid_cols[idx]:
                st.markdown(f"<h4 style='text-align: center; margin-bottom:2px;'>{q_num}</h4>", unsafe_with_html=True)
                st.markdown(f"<p style='text-align: center; color: gray; font-size: 11px;'>Key: {st.session_state.answer_key[q_num]}</p>", unsafe_with_html=True)
                
                q_df = df[df["question"] == q_num].copy()
                
                if not q_df.empty:
                    q_df = q_df.sort_values(by="is_perfect", ascending=True)
                    
                    dot_stack_html = "<div style='display: flex; flex-direction: column-reverse; align-items: center; border: 1px solid #ddd; padding: 10px; border-radius: 5px; min-height: 250px; justify-content: flex-start;'>"
                    
                    for _, row in q_df.iterrows():
                        color = "#2ecc71" if row["is_correct"] else "#e74c3c"
                        initial = row["student"][0].upper()
                        tooltip_text = f"{row['student']} submitted: {row['answer']}"
                        
                        if row["is_perfect"]:
                            dot_stack_html += f'<div class="rainbow-dot" title="{tooltip_text}">{initial}</div>'
                        else:
                            dot_stack_html += f'<div class="normal-dot" style="background-color: {color};" title="{tooltip_text}">{initial}</div>'
                    
                    dot_stack_html += "</div>"
                    st.markdown(dot_stack_html, unsafe_with_html=True)
                else:
                    st.markdown("<div style='text-align: center; color: gray; font-style: italic; padding-top: 50px;'>Empty</div>", unsafe_with_html=True)

    with col2:
        st.subheader("📊 Question Accuracy Analytics")
        
        q_accuracy = df.groupby("question").agg(
            correct_answers=("is_correct", "sum"),
            total_answers=("is_correct", "count")
        ).reset_index()
        
        q_accuracy["accuracy_pct"] = (q_accuracy["correct_answers"] / q_accuracy["total_answers"]) * 100
        
        all_q_df = pd.DataFrame({"question": sorted_questions})
        q_accuracy = pd.merge(all_q_df, q_accuracy, on="question", how="left").fillna(0)

        q_accuracy_sorted = q_accuracy.sort_values(by="accuracy_pct", ascending=True)

        st.bar_chart(
            data=q_accuracy_sorted,
            x="question",
            y="accuracy_pct",
            color="#2c3e50",
            use_container_width=True
        )
        
        st.dataframe(
            q_accuracy_sorted[["question", "accuracy_pct"]].rename(
                columns={"question": "Question", "accuracy_pct": "Accuracy %"}
            ),
            hide_index=True,
            use_container_width=True
        )
