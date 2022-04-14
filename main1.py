from flask import Flask
from flask import render_template, redirect
from date import db_session
from date.users import User
from date.products import Product
from date.baskets import Basket
from forms.user_form import *
from forms.product_form import ProductForm
from flask_login import LoginManager, login_user, current_user, login_required, logout_user
import product_api
import user_api
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'

login_manager = LoginManager()
login_manager.init_app(app)


@app.route('/')
@app.route('/index', methods=["GET", "POST"])
def index():
    db_sess = db_session.create_session()
    prod = db_sess.query(Product).all()

    return render_template("index.html", prod=prod)


@app.route('/view_basket', methods=["GET", "POST"])
def view_basket():
    db_sess = db_session.create_session()
    basket = db_sess.query(Basket).filter(Basket.user_id == current_user.id).first()
    prod = db_sess.query(Product).all()

    return render_template("view_basket.html", prod=prod, basket=basket)


@app.route('/buy/<int:id>', methods=["GET", "POST"])
def buy(id):
    db_sess = db_session.create_session()
    product = db_sess.query(Product).filter(Product.id == id).first()
    basket = db_sess.query(Basket).filter(Basket.user_id == current_user.id).first()
    basket.products.append(product)
    db_sess.commit()
    return redirect("/")


@app.route('/delete_item/<int:id>', methods=["GET", "POST"])
def delete_item(id):
    db_sess = db_session.create_session()
    product = db_sess.query(Product).filter(Product.id == id).first()
    db_sess.delete(product)
    db_sess.commit()
    return redirect("/")


@app.route('/delete_item_from_basket/<int:id>', methods=["GET", "POST"])
def delete_item_from_basket(id):
    db_sess = db_session.create_session()
    product = db_sess.query(Product).filter(Product.id == id).first()
    basket = db_sess.query(Basket).filter(Basket.user_id == current_user.id).first()
    basket.products.remove(product)
    db_sess.commit()
    return redirect("/view_basket")


@app.route('/book/<int:id>', methods=["GET", "POST"])
def book(id):
    db_sess = db_session.create_session()
    product = db_sess.query(Product).filter(Product.id == id).first()
    basket = db_sess.query(Basket).filter(Basket.user_id == current_user.id).first()
    user = db_sess.query(User).filter(User.id == current_user.id).first()
    if product.price <= user.money and product.count > 0:
        user.money -= product.price
        product.count -= 1
        basket.products.remove(product)
        db_sess.commit()
        basket = db_sess.query(Basket).filter(Basket.user_id == current_user.id).first()
        prod = db_sess.query(Product).all()
        return render_template("view_basket.html", prod=prod, basket=basket, message='Поздравляем с удачной покупкой')
    basket = db_sess.query(Basket).filter(Basket.user_id == current_user.id).first()
    prod = db_sess.query(Product).all()
    return render_template("view_basket.html", prod=prod, basket=basket,
                           message='Товар закончился или недостаточно средств на счету')


@app.route('/main', methods=["GET", "POST"])
def main():
    db_session.global_init("db/shop.db")
    db_sess = db_session.create_session()
    db_sess.commit()
    app.register_blueprint(product_api.blueprint)
    app.register_blueprint(user_api.blueprint)
    app.run()


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/register', methods=['GET', 'POST'])
def reqister():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        user = User(
            name=form.name.data,
            surname=form.surname.data,
            email=form.email.data,
            money=0
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        user_for_basket = db_sess.query(User).filter(User.name == user.name, User.surname == user.surname).first()
        basket = Basket(
            user_id=user_for_basket.id,
        )
        db_sess.add(basket)
        db_sess.commit()
        return redirect('/login')
    return render_template('register.html', title='Registration', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if form.email.data == form.password.data:
            return redirect("/")
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            prod = db_sess.query(Product).all()
            return render_template('index.html', name=user.name, prod=prod)
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/money_add', methods=['GET', 'POST'])
def money_add():
    form = MoneyAddForm()
    if form.validate_on_submit():
        if form.add_money.data <= 0:
            return render_template('money_add.html', title='Пополнение баланса', form=form,
                                   message='Должно быть положительное число')
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.id == current_user.id).first()
        summa = form.add_money.data + user.money
        user.money = summa
        db_sess.merge(user)
        db_sess.commit()
        return redirect('/')
    return render_template('money_add.html', title='Пополнение баланса', form=form)


@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    form = ProductForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        if db_sess.query(Product).filter(User.name == form.name.data).first():
            return render_template('add_product.html', title='Добавление товара',
                                   form=form,
                                   message="Такой продукт уже есть")
        prod = Product(
            name=form.name.data,
            type=form.type.data,
            price=form.price.data,
            count=form.count.data,
            description=form.description.data
        )
        db_sess.add(prod)
        db_sess.commit()
        return redirect('/add_product')
    return render_template('add_product.html', form=form)


@app.route('/dop_info', methods=['GET', 'POST'])
def dop_info():
    form = LoginForm()
    db_sess = db_session.create_session()
    prod = db_sess.query(Product).all()
    img = open()
    return render_template('dop_info.html', form=form, img=img)


if __name__ == '__main__':
    main()
