from flask import request, session
from flask_login import current_user

try:
    from flask_wtf import FlaskForm
except:
    from flask_wtf import Form as FlaskForm

from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import ValidationError, DataRequired, Email, \
    EqualTo, Optional
from billtracker.models import User

import sys


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[Optional(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Repeat Password',
                              validators=[DataRequired(), EqualTo('password')])

    # There's no way to get a field's label at validate() time.
    # But it's possible to get the contents of a StringField.
    # So make the captcha question a readonly string field,
    # out of the tab order; it will be styled with CSS to make
    # it not look like an input field.
    capq = StringField("question",
                       render_kw={ "readonly": True,  "tabIndex":"-1" })
    capa = StringField("question", validators=[DataRequired()])

    submit = SubmitField('Register')

    def validate(self, *args, **kwargs):
        if not super().validate(*args, **kwargs):
            return False
        return True

    def validate_capa(self, capa):
        if not self.captcha:
            print("* validate_capa has no captcha object", file=sys.stderr)

        if 'captcha' in session:
            question = session['captcha']
            if question != self.capq.data:
                print("validate_capq: '%s' didn't match session '%s'"
                      % (self.capq.data, session['captcha']),
                      request.remote_addr, file=sys.stderr)
        else:
            print("no captcha in session", file=sys.stderr)

        if not question:
            print("validate_capa: Couldn't get captcha question from session",
                  request.remote_addr, file=sys.stderr)
            question = self.capq.data

        if not self.captcha.is_answer_correct(capa.data, question=question):
            print("validate_capa: Wrong answer '%s' for captcha question '%s'"
                  % (capa.data, question), request.remote_addr,
                  file=sys.stderr)
            print("  Valid answers are", self.captcha.QandA[question])

            raise ValidationError("No, try again")

    def validate_username(self, username):
        # Some simple logic to guard against attacks,
        # like where spammers put spam with links in the username field
        # hoping that the confirmation mail will send their spam payload.
        if '://' in username.data:
            print("ATTACK ALERT: Bogus username from IP", request.remote_addr,
                  ":", username.data, file=sys.stderr)
            raise ValidationError("That doesn't look like a username")
        if len(username.data) > 60:
            print("ATTACK ALERT: Long username from IP", request.remote_addr,
                  ":", username.data, file=sys.stderr)
            raise ValidationError("Please use a shorter username")

        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            print("Someone tried to re-use username", username.data,
                  "from IP", request.remote_addr, file=sys.stderr)
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            print("WARNING: Someone tried to re-use existing email",
                  email.data, "from IP", request.remote_addr, file=sys.stderr)
            raise ValidationError('That email address is already in use.')


class AddBillsForm(FlaskForm):
    billno = StringField('Bill Designation (e.g. SB21)',
                          validators=[DataRequired()])
    submit = SubmitField('Track Bills')
    billhelp = "Tip: You can enter multiple bill numbers" \
        " separated by commas, e.g. SB21, HR17"

    def validate_billno(self, billno):
        designation = billno.data
        designation = designation.upper()
        if designation[0] not in ['S', 'H', 'J']:
            raise ValidationError('Bills should start with S, H or J.')

        billno.data = designation


class UserSettingsForm(FlaskForm):
    email = StringField('Email', validators=[Optional(), Email()])
    password = PasswordField('New Password')
    password2 = PasswordField('Repeat New Password',
                              validators=[EqualTo('password')])
    submit = SubmitField('Update Settings')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None and user.username != current_user.username:
            raise ValidationError('That email address is already in use.')

class PasswordResetForm(FlaskForm):
    username = StringField('Email', validators=[DataRequired()])
    submit = SubmitField('Send Password Reset')

    # See comment under RegistrationForm
    capq = StringField("question",
                       render_kw={ "readonly": True,  "tabIndex":"-1" })
    capa = StringField("question", validators=[DataRequired()])

    def validate_capa(self, capa):
        if not self.captcha:
            print("* validate_capa has no captcha object", file=sys.stderr)

        if 'captcha' in session:
            question = session['captcha']
            if question != self.capq.data:
                print("WARNING validating password reset: "
                      "capq '%s' didn't match session '%s'"
                      % (self.capq.data, session['captcha']),
                      file=sys.stderr)
        else:
            print("no captcha in session", file=sys.stderr)

        if not question:
            print("** Couldn't get captcha question from session",
                  file=sys.stderr)
            question = self.capq.data

        if not self.captcha.is_answer_correct(capa.data, question=question):
            raise ValidationError("No, try again")
