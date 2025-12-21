# update_db.py
from main import db, app, AI_model, ChatSession, Message
from sqlalchemy import inspect, text

with app.app_context():
    inspector = inspect(db.engine)

    # Проверяем существующие таблицы
    tables = inspector.get_table_names()
    print("Существующие таблицы:", tables)

    # Проверяем колонки chat_session
    if 'chat_session' in tables:
        columns = [col['name'] for col in inspector.get_columns('chat_session')]
        print("Колонки chat_session:", columns)

        # Добавляем недостающие колонки
        if 'chat_type' not in columns:
            print("Добавляем chat_type в chat_session...")
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE chat_session ADD COLUMN chat_type VARCHAR(20) DEFAULT 'text'"))
                conn.commit()

        if 'created_at' not in columns:
            print("Добавляем created_at в chat_session...")
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE chat_session ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP"))
                conn.commit()

    # Проверяем колонки messages
    if 'messages' in tables:
        columns = [col['name'] for col in inspector.get_columns('messages')]
        print("Колонки messages:", columns)

        # Добавляем недостающие колонки
        if 'image_data' not in columns:
            print("Добавляем image_data в messages...")
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE messages ADD COLUMN image_data TEXT"))
                conn.commit()

        if 'style' not in columns:
            print("Добавляем style в messages...")
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE messages ADD COLUMN style VARCHAR(50)"))
                conn.commit()

        if 'created_at' not in columns:
            print("Добавляем created_at в messages...")
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE messages ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP"))
                conn.commit()

    # Добавляем AI модели если их нет
    if not AI_model.query.first():
        print("Добавляем AI модели...")
        ai_models = [
            AI_model(ai_name='Text Generator', token='text_model', limit=1000),
            AI_model(ai_name='Image Generator', token='image_model', limit=100)
        ]
        db.session.add_all(ai_models)
        db.session.commit()

    print("База данных обновлена!")