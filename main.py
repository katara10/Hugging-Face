from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash


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

    # Связь: одна AI модель используется во многих чат-сессиях
    chat_sessions = db.relationship('ChatSession', backref='ai_model', lazy=True)


class ChatSession(db.Model):
    __tablename__ = 'chat_session'

    s_id = db.Column(db.Integer, primary_key=True)
    s_u_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    s_ai_id = db.Column(db.Integer, db.ForeignKey('AI_model.ai_id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)

    # Связь: одна чат-сессия содержит много сообщений
    messages = db.relationship('Message', backref='chat_session', lazy=True)


class Message(db.Model):
    __tablename__ = 'messages'

    m_id = db.Column(db.Integer, primary_key=True)
    m_s_id = db.Column(db.Integer, db.ForeignKey('chat_session.s_id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(50), nullable=False)


# Создание таблиц
with app.app_context():
    db.create_all()


@app.route('/')
def home():
    return redirect(url_for('login'))


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
            return redirect(url_for('personal_account'))
        else:
            flash('Invalid username or password')

    return render_template('login.html')

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
        # Получаем данные из формы
        username = request.form.get('firstname', '').title()
        email = request.form.get('email', '')
        password = request.form.get('pasvord', '')

        # Сохраняем значения для повторного отображения в форме
        value_1, value_2, value_3 = username, password, email

        # Валидация данных
        if not username:
            error_1 = 'Enter the user name'
        if not email:
            error_3 = 'Enter your email address'
        if not password:
            error_2 = 'Enter the password'

        # Если есть ошибки валидации, возвращаем форму с ошибками
        if any([error_1, error_2, error_3]):
            return render_template('registration.html',
                                   error_1=error_1, error_2=error_2, error_3=error_3,
                                   system_error=system_error,
                                   value_1=value_1, value_2=value_2, value_3=value_3)

        try:
            # Проверяем, существует ли пользователь с таким именем или email
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

            # Создаем нового пользователя
            hashed_password = generate_password_hash(password)
            new_user = User(
                username=username,
                email=email,
                password=hashed_password
            )

            db.session.add(new_user)
            db.session.commit()

            # Сохраняем пользователя в сессии
            session.permanent = True
            session['name'] = username
            session['email'] = email
            session['user_id'] = new_user.id  # ДОБАВЛЕНО: сохраняем ID пользователя

            return redirect("/personal_account") # ФАЙЛ С ЗАПРОСАМИ

        except Exception as e:
            db.session.rollback()
            system_error = f'A registration error: {str(e)}'
            return render_template('registration.html',
                                   error_1=error_1, error_2=error_2, error_3=error_3,
                                   system_error=system_error,
                                   value_1=value_1, value_2=value_2, value_3=value_3)


@app.route('/personal_account')
def personal_account():
    if 'name' not in session:  # ИСПРАВЛЕНО: проверяем только имя
        flash('Пожалуйста, войдите в систему')
        return redirect(url_for('login'))

    # Получаем user_id из сессии или из базы данных
    user_id = session.get('user_id')
    if not user_id:
        # Если user_id нет в сессии, получаем его из базы данных
        user = User.query.filter_by(username=session['name']).first()
        if user:
            user_id = user.id
            session['user_id'] = user_id  # Сохраняем в сессии на будущее
        else:
            flash('Ошибка: пользователь не найден')
            return redirect(url_for('login'))

    user_chat_sessions = ChatSession.query.filter_by(s_u_id=user_id).all()
    return render_template('personal_account.html',
                           username=session['name'],
                           chat_sessions=user_chat_sessions)

if __name__ == '__main__':
    app.run(debug=True) # Запускаем сайт