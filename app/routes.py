from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from app import app, db
from app.forms import LoginForm, RegistrationForm, AddBillsForm
from app.models import User


@app.route('/')
@app.route('/index')
@login_required
def index():
    return render_template('index.html', title='Home')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

# The mega tutorial called this /register,
# but flask seems to have a problem calling anything /register.
# As long as it's named something else, this works.
# I'm not sure why there are methods defined here,
# nothing's passed to this page.
@app.route('/newaccount', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

# in templates/index.html, {{ url_for(addbills) }} doesn't work. Why not?

@app.route('/addbills', methods=['GET', 'POST'])
@login_required
def addbills():
    form = AddBillsForm()
    if form.validate_on_submit():
        billnum = form.billnum.data
        print("addbills(): billnum =", billnum)
        # do stuff with valid form
        # then redirect to "end" the form
        # return redirect(url_for('addbills'))

        # Clear the form field
        form.billnum.data = ""
    else:
        billnum = None

    return render_template('addbills.html', title='Add More Bills', form=form,
                           billnum=billnum)
