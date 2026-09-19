import uuid
from datetime import datetime

import streamlit as st

import gdrive_storage as gdrive

st.set_page_config(page_title="Авторевью кода — трекер", layout="wide")

st.markdown(
    """
    <style>
    html, body, [class*="css"] { font-size: 19px; }
    h1 { font-size: 2.6rem !important; }
    h2 { font-size: 2rem !important; }
    h3 { font-size: 1.6rem !important; }
    [data-testid="stSidebar"] { font-size: 1.1rem; min-width: 300px; }
    [data-testid="stSidebar"] label { font-size: 1.15rem !important; }
    [data-testid="stMetricValue"] { font-size: 2rem !important; }
    [data-testid="stMetricLabel"] { font-size: 1.1rem !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        font-size: 1.15rem;
        padding: 14px 22px;
        height: auto;
    }
    .stButton button, .stDownloadButton button, .stFormSubmitButton button {
        font-size: 1.05rem;
        padding: 0.6em 1.3em;
        border-radius: 10px;
    }
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
        font-size: 1.1rem !important;
    }
    [data-testid="stMarkdownContainer"] p { font-size: 1.1rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

ROLES =["Бэкенд", "Фронтенд", "DevOps", "Аналитика", "Тестирование", "ML"]
ROLE_ICONS = {
    "Бэкенд": "⚙️",
    "Фронтенд": "🎨",
    "DevOps": "🚀",
    "Аналитика": "📊",
    "Тестирование": "🧪",
    "ML": "🤖",
}

STAGE_STATUS_OPTIONS = ["Не начато", "В процессе", "На проверке", "Готово", "Заблокировано"]
STAGE_STATUS_COLOR = {
    "Не начато": "🔘",
    "В процессе": "🟡",
    "На проверке": "🔵",
    "Готово": "🟢",
    "Заблокировано": "🔴",
}

TASK_STATUS_OPTIONS = ["К выполнению", "В работе", "На проверке", "Готово", "Не будет выполнено"]
TASK_STATUS_COLOR = {
    "К выполнению": "⚪",
    "В работе": "🟡",
    "На проверке": "🔵",
    "Готово": "🟢",
    "Не будет выполнено": "⚫",
}


def empty_role():
    return {"status": "Не начато", "description": "", "documents": [], "tasks": [], "notes": []}


def persist():
    if not gdrive.is_configured():
        return
    try:
        gdrive.save_state({"roles": st.session_state.roles})
        st.session_state["_save_error"] = None
    except Exception as e:
        st.session_state["_save_error"] = str(e)


if "roles" not in st.session_state:
    loaded_roles = None
    load_error = None
    if gdrive.is_configured():
        try:
            loaded = gdrive.load_state()
            loaded_roles = loaded.get("roles") if loaded else None
        except Exception as e:
            load_error = str(e)
    st.session_state.roles = loaded_roles or {role: empty_role() for role in ROLES}
    st.session_state["_load_error"] = load_error
    st.session_state["_save_error"] = None

st.title("📌 Трекер этапов — Авторевью кода")
st.caption("Прототип для командного планирования: документы, задачи и отметки по каждой роли.")

if not gdrive.is_configured():
    st.warning(
        "Google Drive не подключён — данные сохраняются только в этой сессии браузера "
        "и пропадут при перезапуске. Задайте GDRIVE_FOLDER_ID и выполните python gdrive_auth.py.",
        icon="⚠️",
    )
elif st.session_state.get("_load_error"):
    st.error(f"Не удалось загрузить данные из Google Drive: {st.session_state['_load_error']}")
elif st.session_state.get("_save_error"):
    st.error(f"Не удалось сохранить данные в Google Drive: {st.session_state['_save_error']}")
else:
    st.caption("☁️ Подключено к Google Drive — изменения сохраняются автоматически.")

page = st.sidebar.radio(
    "Разделы",
    ["📊 Обзор проекта"] + [f"{ROLE_ICONS[r]} {r}" for r in ROLES],
)

st.sidebar.divider()
st.sidebar.caption("Позже здесь могут быть: фильтр по спринту, привязка к задачам Jira/Trello, права доступа.")


def render_overview():
    st.subheader("Статус по ролям")

    cols = st.columns(len(ROLES))
    for col, role in zip(cols, ROLES):
        data = st.session_state.roles[role]
        total = len(data["tasks"])
        done = sum(1 for t in data["tasks"] if t["status"] == "Готово")
        with col:
            st.markdown(f"**{ROLE_ICONS[role]} {role}**")
            st.write(STAGE_STATUS_COLOR[data["status"]] + " " + data["status"])
            st.caption(f"Задачи: {done}/{total} · Документы: {len(data['documents'])}")
            if total:
                st.progress(done / total)

    st.divider()
    st.subheader("Последние отметки по всем ролям")

    all_notes = [
        {"Роль": role, **note}
        for role, data in st.session_state.roles.items()
        for note in data["notes"]
    ]
    if all_notes:
        all_notes.sort(key=lambda n: n["Время"], reverse=True)
        st.table(all_notes)
    else:
        st.info("Отметок пока нет — добавьте их на страницах ролей слева.")


def render_description_tab(data):
    new_status = st.selectbox(
        "Статус этапа", STAGE_STATUS_OPTIONS, index=STAGE_STATUS_OPTIONS.index(data["status"])
    )
    new_description = st.text_area(
        "Описание работы (как в тикете)",
        value=data["description"],
        height=320,
        placeholder="Контекст, цель этапа, критерии готовности, ссылки на связанные тикеты...",
    )
    if new_status != data["status"] or new_description != data["description"]:
        data["status"] = new_status
        data["description"] = new_description
        persist()


def render_documents_tab(data, role):
    uploaded_files = st.file_uploader(
        "Загрузить документы для этапа",
        accept_multiple_files=True,
        key=f"uploader_{role}",
    )
    if uploaded_files:
        existing = {(d["name"], d["size"]) for d in data["documents"]}
        for f in uploaded_files:
            if (f.name, f.size) in existing:
                continue
            if gdrive.is_configured():
                try:
                    file_id, link = gdrive.upload_document(
                        f.name, f.getvalue(), f.type or "application/octet-stream"
                    )
                    data["documents"].append(
                        {
                            "id": file_id,
                            "name": f.name,
                            "size": f.size,
                            "storage": "drive",
                            "link": link,
                            "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        }
                    )
                except Exception as e:
                    st.error(f"Не удалось загрузить «{f.name}» в Google Drive: {e}")
            else:
                data["documents"].append(
                    {
                        "id": uuid.uuid4().hex,
                        "name": f.name,
                        "size": f.size,
                        "storage": "local",
                        "data": f.getvalue(),
                        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    }
                )
        persist()

    st.divider()

    if not data["documents"]:
        st.info("Документов пока нет.")
        return

    for doc in list(data["documents"]):
        with st.container(border=True):
            c1, c2 = st.columns([5, 2])
            badge = "☁️" if doc["storage"] == "drive" else "💾 (только в этой сессии)"
            c1.markdown(f"📄 **{doc['name']}** {badge}")
            c1.caption(f"{doc['size'] / 1024:.1f} КБ · загружен {doc['uploaded_at']}")
            with c2:
                if doc["storage"] == "drive":
                    st.link_button("↗ Открыть в Drive", doc["link"], use_container_width=True)
                else:
                    st.download_button(
                        "⬇️ Скачать",
                        data=doc["data"],
                        file_name=doc["name"],
                        key=f"dl_{doc['id']}",
                        use_container_width=True,
                    )
                if st.button("🗑 Удалить", key=f"del_doc_{doc['id']}", use_container_width=True):
                    if doc["storage"] == "drive":
                        try:
                            gdrive.delete_document(doc["id"])
                        except Exception as e:
                            st.warning(f"Не удалось удалить файл из Drive: {e}")
                    data["documents"].remove(doc)
                    persist()
                    st.rerun()


def render_tasks_tab(data, role):
    with st.form(key=f"task_form_{role}", clear_on_submit=True):
        c1, c2 = st.columns([3, 2])
        title = c1.text_input("Новая задача")
        assignee = c2.text_input("Исполнитель")
        if st.form_submit_button("➕ Добавить задачу", use_container_width=True) and title:
            data["tasks"].append(
                {
                    "id": uuid.uuid4().hex,
                    "title": title,
                    "assignee": assignee or "—",
                    "status": "К выполнению",
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                }
            )
            persist()

    st.divider()

    if not data["tasks"]:
        st.info("Задач пока нет.")
        return

    for task in list(data["tasks"]):
        with st.container(border=True):
            c1, c2, c3 = st.columns([4, 2, 2])
            done = task["status"] == "Готово"
            label = f"~~{task['title']}~~" if done else f"**{task['title']}**"
            c1.markdown(f"### {TASK_STATUS_COLOR[task['status']]}")
            c1.markdown(label)
            c1.caption(f"👤 {task['assignee']} · создано {task['created_at']}")
            new_task_status = c2.selectbox(
                "Статус",
                TASK_STATUS_OPTIONS,
                index=TASK_STATUS_OPTIONS.index(task["status"]),
                key=f"status_{task['id']}",
            )
            if new_task_status != task["status"]:
                task["status"] = new_task_status
                persist()
            with c3:
                st.write("")
                if st.button("🗑 Удалить", key=f"del_task_{task['id']}", use_container_width=True):
                    data["tasks"].remove(task)
                    persist()
                    st.rerun()


def render_notes_tab(data, role):
    with st.form(key=f"note_form_{role}", clear_on_submit=True):
        author = st.text_input("Автор отметки")
        text = st.text_area("Текст отметки", height=100)
        if st.form_submit_button("➕ Добавить отметку") and text:
            data["notes"].append(
                {
                    "Время": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Автор": author or "Аноним",
                    "Отметка": text,
                }
            )
            persist()

    st.divider()

    if data["notes"]:
        for note in reversed(data["notes"]):
            with st.container(border=True):
                st.markdown(f"**{note['Автор']}** · {note['Время']}")
                st.write(note["Отметка"])
    else:
        st.info("Отметок по этому этапу пока нет.")


if page == "📊 Обзор проекта":
    render_overview()
else:
    role = page.split(" ", 1)[1]
    data = st.session_state.roles[role]

    st.subheader(f"{ROLE_ICONS[role]} {role}")

    tab_desc, tab_docs, tab_tasks, tab_notes = st.tabs(
        ["📝 Описание", "📁 Документы", "✅ Задачи", "💬 Отметки"]
    )
    with tab_desc:
        render_description_tab(data)
    with tab_docs:
        render_documents_tab(data, role)
    with tab_tasks:
        render_tasks_tab(data, role)
    with tab_notes:
        render_notes_tab(data, role)
