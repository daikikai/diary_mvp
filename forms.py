from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email

class EntryForm(FlaskForm):
    title = StringField("タイトル", validators=[DataRequired(), Length(max=120)])
    body = TextAreaField("本文", validators=[DataRequired()])
    image = FileField("画像（任意）",
        validators=[FileAllowed(["jpg","jpeg","png","gif","webp"], "画像のみ")])
    submit = SubmitField("保存")

class LoginForm(FlaskForm):
    email = StringField("メールアドレス", validators=[DataRequired(), Email()])
    password = PasswordField("パスワード", validators=[DataRequired()])
    submit = SubmitField("ログイン")