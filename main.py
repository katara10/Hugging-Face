from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import base64
from io import BytesIO
from text_generator import get_ai_text
from img_generator import generate_image

app = Flask(__name__)
app.config['SECRET_KEY'] = '5457fae2a71f9331bf4bf3dd6813f90abeb33839f4608755ce301b9321c6'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pp3.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# Описание таблиц
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    lg = db.Column(db.Integer, default=0)

    chat_sessions = db.relationship('ChatSession', backref='user', lazy=True)


class AI_model(db.Model):
    __tablename__ = 'AI_model'

    ai_id = db.Column(db.Integer, primary_key=True)
    ai_name = db.Column(db.String(100), nullable=False)
    token = db.Column(db.String(255), nullable=False)
    limit = db.Column(db.Integer)

    chat_sessions = db.relationship('ChatSession', backref='ai_model', lazy=True)


class ChatSession(db.Model):
    __tablename__ = 'chat_session'

    s_id = db.Column(db.Integer, primary_key=True)
    s_u_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    s_ai_id = db.Column(db.Integer, db.ForeignKey('AI_model.ai_id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    chat_type = db.Column(db.String(20), default='text')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    messages = db.relationship('Message', backref='chat_session', lazy=True)


class Message(db.Model):
    __tablename__ = 'messages'

    m_id = db.Column(db.Integer, primary_key=True)
    m_s_id = db.Column(db.Integer, db.ForeignKey('chat_session.s_id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(50), nullable=False)
    image_data = db.Column(db.Text)
    style = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# Создание таблиц
with app.app_context():
    try:
        db.create_all()

        # Проверяем и добавляем необходимые AI модели если их нет
        if not AI_model.query.first():
            ai_models = [
                AI_model(ai_name='Text Generator', token='text_model', limit=1000),
                AI_model(ai_name='Image Generator', token='image_model', limit=100)
            ]
            db.session.add_all(ai_models)
            db.session.commit()
            print("AI модели добавлены в базу данных")
    except Exception as e:
        print(f"Ошибка при создании БД: {e}")


@app.route('/')
def home():
    return render_template('main-page.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session.permanent = True
            session['name'] = user.username
            session['user_id'] = user.id
            return redirect(url_for('chat_page_text'))
        else:
            flash('Invalid username or password')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Вы успешно вышли из системы')
    return redirect(url_for('login'))


@app.route('/registration', methods=['POST', 'GET'])
def registration():
    error_1 = ''
    error_2 = ''
    error_3 = ''
    value_1, value_2, value_3 = '', '', ''
    system_error = ''

    if request.method == 'GET':
        return render_template('registration.html',
                               error_1=error_1, error_2=error_2, error_3=error_3,
                               system_error=system_error,
                               value_1=value_1, value_2=value_2, value_3=value_3)

    elif request.method == 'POST':
        username = request.form.get('firstname', '').title()
        email = request.form.get('email', '')
        password = request.form.get('pasvord', '')

        value_1, value_2, value_3 = username, password, email

        if not username:
            error_1 = 'Enter the user name'
        if not email:
            error_3 = 'Enter your email address'
        if not password:
            error_2 = 'Enter the password'

        if any([error_1, error_2, error_3]):
            return render_template('registration.html',
                                   error_1=error_1, error_2=error_2, error_3=error_3,
                                   system_error=system_error,
                                   value_1=value_1, value_2=value_2, value_3=value_3)

        try:
            existing_user = User.query.filter(
                (User.username == username) | (User.email == email)
            ).first()

            if existing_user:
                if existing_user.username == username:
                    error_1 = 'The username is already taken'
                if existing_user.email == email:
                    error_3 = 'email has already been registered'

                return render_template('registration.html',
                                       error_1=error_1, error_2=error_2, error_3=error_3,
                                       system_error=system_error,
                                       value_1=value_1, value_2=value_2, value_3=value_3)

            hashed_password = generate_password_hash(password)
            new_user = User(
                username=username,
                email=email,
                password=hashed_password
            )

            db.session.add(new_user)
            db.session.commit()

            session.permanent = True
            session['name'] = username
            session['email'] = email
            session['user_id'] = new_user.id

            return redirect("/chat_page_text")

        except Exception as e:
            db.session.rollback()
            system_error = f'A registration error: {str(e)}'
            return render_template('registration.html',
                                   error_1=error_1, error_2=error_2, error_3=error_3,
                                   system_error=system_error,
                                   value_1=value_1, value_2=value_2, value_3=value_3)


@app.route('/chat_page_text')
def chat_page_text():
    if 'name' not in session:
        flash('Пожалуйста, войдите в систему')
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    if not user_id:
        user = User.query.filter_by(username=session['name']).first()
        if user:
            user_id = user.id
            session['user_id'] = user_id
        else:
            flash('Ошибка: пользователь не найден')
            return redirect(url_for('login'))

    # Получаем text чаты пользователя
    text_ai = AI_model.query.filter_by(token='text_model').first()
    if not text_ai:
        flash('Ошибка: модель для текста не найдена')
        return redirect(url_for('home'))

    user_chat_sessions = ChatSession.query.filter_by(
        s_u_id=user_id,
        s_ai_id=text_ai.ai_id
    ).all()

    # Создаем новый text чат если нет
    if not user_chat_sessions:
        new_chat = ChatSession(
            s_u_id=user_id,
            s_ai_id=text_ai.ai_id,
            title='Новый текстовый чат',
            chat_type='text'
        )
        db.session.add(new_chat)
        db.session.commit()
        user_chat_sessions = [new_chat]

    current_chat_id = user_chat_sessions[0].s_id
    session['current_chat_id'] = current_chat_id

    # Получаем сообщения текущего чата
    chat_messages = Message.query.filter_by(m_s_id=current_chat_id) \
        .order_by(Message.created_at.asc()) \
        .all()

    return render_template('chat_page_text.html',
                           username=session['name'],
                           chat_sessions=user_chat_sessions,
                           current_chat_id=current_chat_id,
                           chat_messages=chat_messages)


@app.route('/generate_text', methods=['POST'])
def generate_text():
    """Генерация текстового ответа"""
    if 'user_id' not in session:
        return jsonify({'error': 'Не авторизован'}), 401

    data = request.get_json()
    prompt = data.get('prompt', '').strip()

    if not prompt:
        return jsonify({'error': 'Введите запрос'}), 400

    try:
        current_chat_id = session.get('current_chat_id')

        # Сохраняем сообщение пользователя
        user_message = Message(
            m_s_id=current_chat_id,
            content=prompt,
            role='user'
        )
        db.session.add(user_message)
        db.session.flush()

        # Генерируем текст
        generated_text = get_ai_text(prompt, thinking=True)

        # Сохраняем ответ ИИ
        ai_message = Message(
            m_s_id=current_chat_id,
            content=generated_text,
            role='assistant'
        )
        db.session.add(ai_message)
        db.session.commit()

        return jsonify({
            'success': True,
            'text': generated_text
        })

    except Exception as e:
        print(f"Ошибка генерации текста: {e}")
        db.session.rollback()
        return jsonify({'error': f'Ошибка генерации: {str(e)}'}), 500


@app.route('/chat_page_image')
def chat_page_image():
    if 'name' not in session:
        flash('Пожалуйста, войдите в систему')
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    if not user_id:
        user = User.query.filter_by(username=session['name']).first()
        if user:
            user_id = user.id
            session['user_id'] = user_id
        else:
            flash('Ошибка: пользователь не найден')
            return redirect(url_for('login'))

    # Получаем image чаты пользователя
    image_ai = AI_model.query.filter_by(token='image_model').first()
    if not image_ai:
        flash('Ошибка: модель для изображений не найдена')
        return redirect(url_for('home'))

    user_chat_sessions = ChatSession.query.filter_by(
        s_u_id=user_id,
        s_ai_id=image_ai.ai_id
    ).all()

    # Создаем новый image чат если нет
    if not user_chat_sessions:
        new_chat = ChatSession(
            s_u_id=user_id,
            s_ai_id=image_ai.ai_id,
            title='Новый чат с изображениями',
            chat_type='image'
        )
        db.session.add(new_chat)
        db.session.commit()
        user_chat_sessions = [new_chat]

    current_chat_id = user_chat_sessions[0].s_id
    session['current_chat_id'] = current_chat_id

    # Получаем сообщения текущего чата
    chat_messages = Message.query.filter_by(m_s_id=current_chat_id) \
        .order_by(Message.created_at.asc()) \
        .all()

    return render_template('chat_page_image.html',
                           username=session['name'],
                           chat_sessions=user_chat_sessions,
                           current_chat_id=current_chat_id,
                           chat_messages=chat_messages)


@app.route('/generate_image', methods=['POST'])
def generate_image_route():
    """Генерация изображения"""
    if 'user_id' not in session:
        return jsonify({'error': 'Не авторизован'}), 401

    data = request.get_json()
    prompt = data.get('prompt', '').strip()
    style = data.get('style', 'реализм')

    if not prompt:
        return jsonify({'error': 'Введите запрос'}), 400

    try:
        current_chat_id = session.get('current_chat_id')

        # Сохраняем сообщение пользователя
        user_message = Message(
            m_s_id=current_chat_id,
            content=f"Запрос: {prompt} (стиль: {style})",
            role='user',
            style=style
        )
        db.session.add(user_message)
        db.session.flush()

        # Генерируем изображение
        image = generate_image(prompt, style, save_image=False)

        # Конвертируем в base64
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

        # Сохраняем сообщение с изображением
        ai_message = Message(
            m_s_id=current_chat_id,
            content=f"Сгенерировано изображение: {prompt}",
            role='assistant',
            image_data=img_base64,
            style=style
        )
        db.session.add(ai_message)
        db.session.commit()

        return jsonify({
            'success': True,
            'image_data': img_base64,
            'message': f"Изображение сгенерировано в стиле {style}"
        })

    except Exception as e:
        print(f"Ошибка генерации: {e}")
        db.session.rollback()
        return jsonify({'error': f'Ошибка генерации: {str(e)}'}), 500


@app.route('/get_chat_messages')
def get_chat_messages():
    """Получение сообщений чата"""
    if 'user_id' not in session:
        return jsonify({'error': 'Не авторизован'}), 401

    chat_id = request.args.get('chat_id', session.get('current_chat_id'))

    messages = Message.query.filter_by(m_s_id=chat_id) \
        .order_by(Message.created_at.asc()) \
        .all()

    messages_list = []
    for msg in messages:
        message_data = {
            'id': msg.m_id,
            'content': msg.content,
            'role': msg.role,
            'timestamp': msg.created_at.strftime('%H:%M') if msg.created_at else '',
            'style': msg.style
        }

        if msg.image_data:
            message_data['image_data'] = msg.image_data

        messages_list.append(message_data)

    return jsonify(messages_list)


if __name__ == '__main__':
    app.run(debug=True)
