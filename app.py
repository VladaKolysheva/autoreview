import streamlit as st

st.title("Моё первое приложение")
st.write("Привет! Это работает 🎉")

name = st.text_input("Как тебя зовут?")
if name:
    st.write(f"Приятно познакомиться, {name}!")

number = st.slider("Выбери число", 0, 100, 50)
st.write(f"Ты выбрал: {number}")