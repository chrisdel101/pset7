import os
import datetime
import re


from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_mail import Mail, Message
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
# app.config.from_envar('APP_SETTINGS')
app.config.from_object(__name__)
app.config.from_pyfile("flask.cfg")

print(app.config['MAIL_SERVER'])
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=465,
    MAIL_USE_SSL=True,
    MAIL_USERNAME = 'mote2zart@gmail.com',
    MAIL_PASSWORD = 'udykkvxnfuwvuxoz'
)



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

mail = Mail(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/contact", methods=['GET', 'POST'])
def contact():
    # form = ContactForm()
    if request.method == 'GET':
        # g = mail.send_message(
        #   'Send Mail tutorial!',
        #   sender="mote2zart@gmail.com",
        #   recipients=['arssonist@yahoo.com'],
        #   body="Congratulations you've succeeded!"

        msg = Message("Hello",
                  sender="mote2zart@gmail.com",
                  recipients=['arssonist@yahoo.com'])
        msg.body = "testing"
        msg.html = "<b>testing</b>"
        mail.send(msg)
        return 'Mail sent'


"""Show portfolio of stocks"""
@app.route("/")
@login_required
def index():
    user_id = session['user_id']
    # select all assets
    assetData = db.execute("SELECT * FROM assets WHERE user_id=(:user_id)", user_id=user_id)
    # select cash
    cash = db.execute("SELECT cash FROM users WHERE id=(:id)", id=user_id)
    cash = cash[0]['cash']
    # loop through data and round all the totals
    for datum in assetData:
        # round and add usd
        datum['total'] = usd(round(datum['total'],2))
        # add usd
    cash = usd(round(cash, 2))
    return render_template("index.html", data=assetData, cash=cash)


# return the purchase ID for buy and sell
def purchaseID():
    last_purchase_id = db.execute("SELECT MAX(purchase_id) from purchases")
    # extract from list and dict
    last_purchase_id = last_purchase_id[0]['MAX(purchase_id)']
    # if no IDs, make first = 1
    if last_purchase_id == None:
        # print("no ids yet, set to one")
        current_purchase_id = 1
    # add one to get id for this purchase
    elif last_purchase_id != None:
        # print('ids there. increment')
        current_purchase_id = last_purchase_id + 1
        # print(f"last id:{last_purchase_id}")
        # print(f"current id:{current_purchase_id}")
    return current_purchase_id


"""Buy shares of stock"""
@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    user_id = session['user_id']
    if request.method == 'POST':
        if not request.form.get("symbol") or not request.form.get('shares'):
            return apology("Must fill in both fields.", 400)
        else:
            # get form values
            symbol = request.form.get("symbol")
            symbol = symbol.upper()
            shares = request.form.get("shares")
            # error handling - fraction/decimals return ValueError
            try:
                shares = int(shares)
                if shares < 0:
                    return apology("Cannot purchase negative shares.", 400)
            except ValueError:
                # print("Could not convert")
                return apology("Only integers a can be entered.", 400)
            # get API INFO
            look_up = lookup(symbol)
            # print(f"lookup:{look_up}")
            if look_up == None:
                return apology("Not a valid ticker symbol.", 400)
            elif look_up != None:
                price = look_up['price']
                # get users cash
                cash = db.execute("SELECT cash FROM users WHERE (:id)=id", id=user_id)
                cash = cash[0]['cash']
                # print(f"cash: {cash}")
                # calculate total price of shares
                sharesValue = price * shares
                # see if user has the money
                cash_after_shares = cash - sharesValue
                if cash_after_shares >= 0:
                    current_purchase_id = purchaseID()
                    # get date
                    current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    # print(f"date: {current_date}")
                    # print(f"shares: {shares}")
                    # print(f"symbol: {symbol}")
                    # print(f"price: {price}")
                    # print(f"sharesValue: {sharesValue}")
                    # print(f"user_id: {user_id}")
                    # print(f"date: {current_date}")
                    # print(f"purchase_id: {current_purchase_id}")
                    # CHECK if user has that stock already
                    check = db.execute("SELECT symbol FROM purchases WHERE symbol=(:symbol)", symbol=symbol)
                    # not already in table
                    # print(f"check: {check}")
                    if check == []:
                        # print("Symbol not there. Add to both tables")
                        # INSERT - insert new row with all purchase table
                        db.execute("INSERT INTO purchases (user_id, shares, symbol, purchase_id, value, date, share_value, type) VALUES (:user_id, :shares, :symbol, :purchase_id, :value,:date, :share_value, :type)", user_id=user_id, shares=shares, symbol=symbol,purchase_id=current_purchase_id, value=sharesValue,date=current_date, share_value=price, type="buy")
                        # INSERT - insert new row into assets table
                        db.execute("INSERT INTO assets (user_id, symbol, shares, total) VALUES (:user_id, :symbol, :shares, :value)", user_id=user_id, shares=shares, symbol=symbol, value=sharesValue)
                        # update user cash after purchase
                        db.execute("UPDATE users SET cash=(:cash) WHERE id=(:user_id)", cash=cash_after_shares,user_id=user_id)
                        # flash on success
                        flash("New stock added.")
                        # redirect to index
                        return redirect(url_for("index"))
                    else:
                        # print('Symnol there. Add to purchase, update assets.')
                         # INSERT - insert new row into purchase table
                        db.execute("INSERT INTO purchases (user_id, shares, symbol, purchase_id, value, date, share_value, type) VALUES (:user_id, :shares, :symbol, :purchase_id, :value,:date, :share_value, :type)", user_id=user_id, shares=shares, symbol=symbol,purchase_id=current_purchase_id, value=sharesValue,date=current_date, share_value=price, type="buy")
                        # SELECT - current valuees from assets
                        # get shares and value already there
                        currentValues = db.execute("SELECT shares, total FROM assets WHERE user_id=(:user_id)", user_id=user_id)
                        #UPDATE - update the assets table
                        # returns a list - get dict out of list
                        currentValues = currentValues[0]
                        currentShares = currentValues['shares']
                        currentTotal = currentValues['total']
                        # add new vals to old ones
                        newShares = currentShares + shares
                        newTotal = currentTotal + sharesValue
                        db.execute("UPDATE assets SET shares=(:shares), total=(:total) WHERE symbol=(:symbol) AND user_id=(:user_id)", shares=newShares, total=newTotal, symbol=symbol, user_id=user_id)
                        # UPDATE user cash after purchase
                        db.execute("UPDATE users SET cash=(:cash) WHERE id=(:user_id)", cash=cash_after_shares,user_id=user_id)
                        # FLASH
                        flash("New stocks added, or combined with others of the same type.")
                        # redirect to index
                        return redirect(url_for("index"))
                # purchase not approved
                else:
                    # FLASH
                    # print("insufficient funds")
                    return redirect(url_for("index"))
    # GET REQUEST
    elif request.method == "GET":
        return render_template("buy.html", method=request.method)
    else:
        return apology("Request must be a GET or a POST", 400)


"""Show history of transactions"""
@app.route("/history")
@login_required
def history():
    user_id = session['user_id']
    purchaseData = db.execute("SELECT symbol, shares, value, date FROM purchases WHERE user_id=(:user_id)", user_id=user_id)
    # loop over shares vals to round numbers
    for datum in purchaseData:
        if(datum['value'] > 0):
            datum['value'] = round(datum['value'],2)
        else:
            datum['value'] = datum['value']
            # call usd
        datum['value'] = usd(datum['value'])

    return render_template("history.html", data=purchaseData)


"""Log user in"""
@app.route("/login", methods=["GET", "POST"])
def login():
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure email was submitted
        if not request.form.get("email"):
            return apology("must provide email", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for email
        rows = db.execute("SELECT * FROM users WHERE email = :email",
                          email=request.form.get("email"))

        # Ensure email exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid email and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        # print('login successful')

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


"""Get stock quote."""
@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == 'POST':
        if not request.form.get("symbol"):
            return apology("Form cannot be blank.", 400)
        else:
            symbol = request.form.get("symbol")
            symbol = symbol.upper()
            result = lookup(symbol)
            if result == None:
                return apology("Not a valid ticker symbol.", 400)
            else:
                # run price through usd function
                result['price'] = usd(result['price'])
                return render_template("quote.html", quote=result, method=request.method)
    elif request.method == 'GET':
        return render_template("quote.html", method=request.method)


"""Register user"""
@app.route("/register", methods=["GET", "POST"])
def register():
    # user GET, then just render template
    if request.method == "POST":
        if not request.form.get("email"):
            return apology("must provide email", 400)
        if not request.form.get("password"):
            return apology("must provide password", 400)
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords must match", 400)

        email = request.form.get("email")
        # # generate password hash
        hash = generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8)
        # check that is email syntax
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash("Not valid email syntax")
            return render_template("register.html")
        email_query = db.execute("SELECT email FROM users WHERE email=(:email)", email=email)
        if email_query != []:
            return apology("That email already exists. Choose another.", 400)

        db.execute("INSERT INTO users (email,hash) VALUES (:email, :hash)", email=email, hash=hash)
        user_id = db.execute("SELECT id FROM users WHERE email=(:email)", email=email)
        session["user_id"] = user_id
        flash("You are registed.")
        return render_template("index.html")

    elif request.method == "GET":
        return render_template('register.html')
    else:
        return "Request type not valid"


"""Sell shares of stock"""
@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    # print('SELL')
    user_id = session['user_id']
    # get value in assets
    assets = db.execute("SELECT * FROM assets WHERE user_id=(:user_id)", user_id=user_id)
    if request.method == 'GET':
        return render_template("sell.html", data=assets)
    elif request.method == 'POST':
        # get input symbol
        symbol = request.form.get("symbol")
        # get input shares to sell
        shares_to_sell = request.form.get("shares")
        # print(f"symbol:{symbol}")
        # print(f"shares_to_sell:{shares_to_sell}")
        # input must be a string
        # if type(shares_to_sell) != str:
        try:
        # convert to int
            shares_to_sell = int(shares_to_sell)
        except ValueError:
            flash("Error: Input is invalid or empty")
            return render_template("sell.html", data=assets)

        # get shares cuurent in table
        sharesData = db.execute("SELECT shares FROM assets WHERE symbol=(:symbol) AND user_id=(:user_id)", user_id=user_id, symbol=symbol)
        sharesData = sharesData[0]['shares']
        # current amount minus ones sehling
        new_shares_amount = sharesData - shares_to_sell
        # print(f"symbol:{symbol}")
        # print(f"shares_to_sell:{shares_to_sell}")
        # print(f"current shares: {sharesData}")
        # print(f"new_shares_amount:{new_shares_amount}")
        # lookup share value at API to get price
        look_up = lookup(symbol)
        look_up_price = look_up['price']
        # print(f"price:{look_up_price}")
        # value of sold shares - number sold * price each
        selling_cash = look_up_price * shares_to_sell
        if new_shares_amount < 0:
            # print("Don't have that many shares")
            return apology("Not enough shares", 400)
        else:
            # insert trans into purchases table
            current_purchase_id = purchaseID()
            current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db.execute("INSERT INTO purchases (user_id, shares, symbol, purchase_id, value, date, share_value, type) VALUES (:user_id, :shares, :symbol, :purchase_id, :value,:date, :share_value, :type)", user_id=user_id, shares=(shares_to_sell * -1), symbol=symbol,purchase_id=current_purchase_id, value=(selling_cash * -1), date=current_date, share_value=look_up_price, type="sell")
            # change share number in table
            db.execute("UPDATE assets SET shares=(:new_shares_amount) WHERE symbol=(:symbol) AND user_id=(:user_id)", new_shares_amount=new_shares_amount, user_id=user_id, symbol=symbol)
            # change total value - multiply remaining shares * price
            currentTotal = db.execute("SELECT total FROM assets WHERE  symbol=(:symbol) AND user_id=(:user_id)", user_id=user_id, symbol=symbol)
            new_total = new_shares_amount * look_up_price
            # print(f"currentTotal:{currentTotal}")
            # print('new_shares_amount * look_up_price = new_total')
            # print(f"new_total: {new_total}")
            db.execute("UPDATE assets SET total=(:new_total) WHERE user_id=(:user_id) AND symbol=(:symbol)", new_total=new_total, user_id=user_id, symbol=symbol)
            # get current cash
            current_cash = db.execute("SELECT cash FROM users WHERE id=(:user_id)", user_id=user_id)
            current_cash = current_cash[0]['cash']
            # print(f"current_cash: {current_cash}")
            # perform addition
            updated_cash = current_cash + selling_cash
            # print(f"updated_cash:{updated_cash}")
            # update cash
            db.execute("UPDATE users SET cash=(:updated_cash) WHERE id=(:user_id)", updated_cash=updated_cash, user_id=user_id)
            flash("Stocks sold")
            return redirect(url_for("index"))

        return render_template("sell.html")


def errorhandler(e):
    """Handle error"""
    return apology(e)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

