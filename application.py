import os
import datetime

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

TEMPLATES_AUTO_RELOAD = True


# Ensure environment variable is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    return render_template("index.html")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    user_id = session['user_id']
    """Buy shares of stock"""
    if request.method == 'POST':
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        shares = int(shares)
        print(f"symbol: {symbol}")
        print(f"shares: {shares}")
        look_up = lookup(symbol)
        print(f"lookup:{look_up}")
        price = look_up['price']
        print(f"lookup: {look_up}")
        print(f"price: {price}")
        # return render_template("buy.html", stock=look_up, symbol=symbol, method=request.method)
        if look_up == None:
            print('Lookup value is none: must retry')
            # "quote.html", quote=result, method=request.method
            return render_template("buy.html", stock=look_up, symbol=symbol, method=request.method)
        elif look_up != None:
            print(session)
            # get users cash
            cash = db.execute("SELECT cash FROM users WHERE (:id)=id", id=user_id)
            print(cash[0])
            cash = cash[0]['cash']
            print(f"cash: {cash}")
            # calculate total price of shares
            sharesPrice = price * shares
            # see if user has the money
            cash_after_shares = cash - sharesPrice
            if cash_after_shares >= 0:
                print('purchase approved')
                # ALLOCATE ID
                # get last purchase ID, and add one to it for this purchase
                last_purchase_id = db.execute("SELECT MAX(purchase_id) from purchases")
                # extract from list and dict
                last_purchase_id = last_purchase_id[0]['MAX(purchase_id)']
                # add one to get id for this purchase
                current_purchase_id = last_purchase_id + 1

                current_date = datetime.datetime.now().strftime("%Y-%m-%d")
                print(f"date: {current_date}")
                # DB LOGIC
                print(f"shares: {shares}")
                print(f"symbol: {symbol}")
                print(f"value: {sharesPrice}")
                print(f"user_id: {user_id}")
                print(f"date: {current_date}")
                print(f"purchase_id: {current_purchase_id}")
                # add = db.execute("INSERT INTO purchases (user_id, shares,symbol,value,purchase_id,date) VALUES (:shares, :symbol, :user_id, :value, :purchase_id, :date)", user_id=user_id, shares=shares,symbol=symbol,value=sharesPrice, purchase_id=current_purchase_id, date=current_date)
                # db.execute("INSERT INTO purchases (user_id, shares,symbol,purchase_id, value,date) VALUES (:user_id, :shares, :symbol, :purchase_id, :value,:date)", user_id=user_id, shares=shares, symbol=symbol,purchase_id=current_purchase_id, value=sharesPrice,date=current_date)

                # db.execute("UPDATE users SET cash=(:cash) WHERE id=(:id)", cash=cash_after_shares,id=user_id)
                return render_template("buy.html", stock=look_up, symbol=symbol, method=request.method)
            # buy and add to DB
                # db.execute("INSERT ")
            else:
                print("not enough dough")
            return render_template("index.html", stock=look_up, symbol=symbol, method=request.method)

        # return render_template("buy.html")
    elif request.method == "GET":
        return render_template("buy.html",method=request.method)
    else:
        return apology("Request must be a GET of a POST", 400)


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        print('login successful')

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


# @app.route("/logout")
# def logout():
#     """Log user out"""

#     # Forget any user_id
#     session.clear()

#     # Redirect user to login form
#     return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == 'POST':
       symbol = request.form.get("quote")
       result = lookup(symbol)
       print(result)
       return render_template("quote.html", quote=result, method=request.method)
    elif request.method == 'GET':
        return render_template("quote.html",method=request.method)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # user GET, then just render template
    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 403)
        if not request.form.get("password"):
            return apology("must provide password", 403)
        elif request.form.get("password") != request.form.get("re-password"):
            return apology("passwords must match", 403)

        # # generate password hash
        username = request.form.get("username")
        hash = generate_password_hash(request.form.get("password"),method='pbkdf2:sha256', salt_length=8)

        db.execute("INSERT INTO users (username,hash) VALUES (:username, :hash)", username = username, hash = hash)
        user_id = db.execute("SELECT id FROM users WHERE (:username)=username", username=username)
        session["user_id"] = user_id
        print(session)

        return render_template("register.html")
        # db.execute("SELECT * FROM users")
        # db.execute(“INSERT INTO users (username, hash) VALUES (:username, :hash)”, username = request.form.get("username"), hash = generate_password_hash(request.form.get("password"),method="pbkdf2:sha256", salt_length=8))
        # db.execute("INSERT INTO users (username, hash)  VALUES(:username, :hash)", username=request.form.get("username"), hash=generate_password_hash(request.form.get("password"),method='pbkdf2:sha256', salt_length=8))
    elif request.method == "GET":
        return render_template('register.html')
    else:
        return "Reques type not validflas"


# @app.route("/sell", methods=["GET", "POST"])
# @login_required
# def sell():
#     """Sell shares of stock"""
#     return apology("TODO")


def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
