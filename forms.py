from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length
from flask_wtf.file import FileField, FileAllowed

class EntryForm(FlaskForm):
    title = StringField("タイトル", validators=[DataRequired(), Length(max=120)])
    body = TextAreaField("本文", validators=[DataRequired()])
    image = FileField("画像（任意）",
        validators=[FileAllowed(["jpg","jpeg","png","gif","webp"], "画像のみ")])
    submit = SubmitField("保存")
