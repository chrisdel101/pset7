import os
import datetime

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
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

@app.route("/lookup")
def lookup_check():
    look_up1 = lookup('GOOG')
    look_up2 = lookup('GOGO')
    print(look_up1)
    print(look_up2)

@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user_id = session['user_id']
    # purchaseData = db.execute("SELECT symbol, shares, share_value, value FROM purchases WHERE user_id=(:user_id)", user_id=user_id)
    # assetData = db.execute("SELECT * FROM assets")
    # cash = db.execute("SELECT cash FROM users WHERE (:id)=id", id=user_id)
    # cash = cash[0]['cash']
    # cash = str(round(cash, 2))

    data = assests_cash(user_id)
    assetData = data[0]
    # loop through data and round all the totals
    for datum in assetData:
        datum['total'] = round(datum['total'],2)
    print(assetData)
    cash = data[1]
    cash = round(cash, 2)

    return render_template("index.html", data=assetData, cash=cash)
    # return render_template("index.html")


# returns list of assets and cash
def assests_cash(user_id):
    # select all assets
    assetData = db.execute("SELECT * FROM assets WHERE user_id=(:user_id)", user_id=user_id)
    # select cash
    cash = db.execute("SELECT cash FROM users WHERE id=(:id)", id=user_id)
    # get cash from dict
    cash = cash[0]['cash']
    # round cash down
    # cash = round(cash, 2)
    return [assetData, cash]



@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    user_id = session['user_id']
    # set blank variable
    # last_purchase_id = ""
    """Buy shares of stock"""
    if request.method == 'POST':
        # get form values
        symbol = request.form.get("symbol")
        symbol = symbol.upper()
        shares = request.form.get("shares")
        shares = int(shares)
        # get API INFO
        look_up = lookup(symbol)
        print(f"lookup:{look_up}")
        if look_up == None:
            print('Lookup value is none: must retry')
            # "quote.html", quote=result, method=request.method
            return render_template("buy.html", stock=look_up, symbol=symbol, method=request.method)
        # return render_template("buy.html", stock=look_up, symbol=symbol, method=request.method)
        elif look_up != None:
            price = look_up['price']
            print(f"price: {price}", type(price))
            # get users cash
            cash = db.execute("SELECT cash FROM users WHERE (:id)=id", id=user_id)
            cash = cash[0]['cash']
            print(f"cash: {cash}")
            # calculate total price of shares
            sharesValue = price * shares
            # see if user has the money
            cash_after_shares = cash - sharesValue
            if cash_after_shares >= 0:
                print('purchase approved')
                # ALLOCATE ID
                # get last purchase ID, if 1 or more add one to it for this purchase
                last_purchase_id = db.execute("SELECT MAX(purchase_id) from purchases")
                # extract from list and dict
                last_purchase_id = last_purchase_id[0]['MAX(purchase_id)']
                # if no IDs, make first = 1
                if last_purchase_id == None:
                    print("no ids yet, set to one")
                    current_purchase_id= 1
                # add one to get id for this purchase
                elif last_purchase_id != None:
                    print('ids there. increment')
                    current_purchase_id = last_purchase_id + 1
                print(f"last id:{last_purchase_id}")
                print(f"current id:{current_purchase_id}")
                # get date
                current_date = datetime.datetime.now().strftime("%Y-%m-%d")
                print(f"date: {current_date}")
                # DB LOGIC
                print(f"shares: {shares}")
                print(f"symbol: {symbol}")
                print(f"price: {price}")
                print(f"sharesValue: {sharesValue}")
                print(f"user_id: {user_id}")
                print(f"date: {current_date}")
                print(f"purchase_id: {current_purchase_id}")
                # CHECK if user has that stock already
                check = db.execute("SELECT symbol FROM purchases WHERE symbol=(:symbol)", symbol=symbol)
                # not already in table
                print(f"check: {check}")
                if check == []:
                    print("Symbol not there. Add to both tables")
                    # INSERT - insert new row with all purchase table
                    db.execute("INSERT INTO purchases (user_id, shares, symbol, purchase_id, value, date, share_value) VALUES (:user_id, :shares, :symbol, :purchase_id, :value,:date, :share_value)", user_id=user_id, shares=shares, symbol=symbol,purchase_id=current_purchase_id, value=sharesValue,date=current_date, share_value=price)
                    # INSERT - insert new row into assets table
                    db.execute("INSERT INTO assets (user_id, symbol, shares, total) VALUES (:user_id, :symbol, :shares, :value)", user_id=user_id, shares=shares, symbol=symbol, value=sharesValue)
                    # update user cash after purchase
                    db.execute("UPDATE users SET cash=(:cash) WHERE id=(:user_id)", cash=cash_after_shares,user_id=user_id)

                    # redirect to index
                    return redirect(url_for("index"))
                else:
                    print('Symnol there. Add to purchase, update assets.')
                     # INSERT - insert new row into purchase table
                    db.execute("INSERT INTO purchases (user_id, shares, symbol, purchase_id, value, date, share_value) VALUES (:user_id, :shares, :symbol, :purchase_id, :value,:date, :share_value)", user_id=user_id, shares=shares, symbol=symbol,purchase_id=current_purchase_id, value=sharesValue,date=current_date, share_value=price)
                    # SELECT - current valuees from assets
                    # get shares and value already there
                    currentValues = db.execute("SELECT shares, total FROM assets WHERE user_id=(:user_id)", user_id=user_id)
                    #UPDATE - update the assets table
                    # returns a list - get dict out of list
                    currentValues = currentValues[0]
                    currentShares = currentValues['shares']
                    currentTotal =  currentValues['total']
                    # add new vals to old ones
                    newShares = currentShares + shares
                    newTotal  = currentTotal + sharesValue
                    db.execute("UPDATE assets SET shares=(:shares), total=(:total)", shares=newShares, total=newTotal)
                    # UPDATE user cash after purchase
                    db.execute("UPDATE users SET cash=(:cash) WHERE id=(:user_id)", cash=cash_after_shares,user_id=user_id)
                    # redirect to index
                    return redirect(url_for("index"))
                    # return render_template("index.html", data=assets, cash=cash)
            # purchase not approved
            else:
                print("insufficient funds")
                return redirect(url_for("index"))
    # GET REQUEST
    elif request.method == "GET":
        return render_template("buy.html",method=request.method)
    else:
        return apology("Request must be a GET or a POST", 400)

# if doesnt'exist
# - insert into purchases
# - insert into assets
# - update cash
# - select assets with index funtion
# - put into index template


# If does exist
# - insert into purchases
# - check assets
# - perform math to update assets
# - update assets
# - update cash
# - select assets with index functoin
# - put into index template

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


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == 'POST':
       symbol = request.form.get("quote")
       symbol = symbol.upper()
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

# - query for list of stocks
# - show list of all stocks and shares

    """Sell shares of stock"""
@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    print('SELL')
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
        if type(shares_to_sell) != str:
            # FLASH
            print("Error: Input is invalid or empty")
            # rerender sell.html
            return render_template("sell.html", data=assets)
        else:
            # convert to int
            shares_to_sell = int(shares_to_sell)
            # get shares cuurent in table
            sharesData = db.execute("SELECT shares FROM assets WHERE symbol=(:symbol) AND user_id=(:user_id)", user_id=user_id, symbol=symbol)
            sharesData = sharesData[0]['shares']
            # current amount minus ones sehling
            new_shares_amount = sharesData - shares_to_sell
            print(f"symbol:{symbol}")
            print(f"shares_to_sell:{shares_to_sell}")
            print(f"current shares: {sharesData}")
            print(f"new_shares_amount:{new_shares_amount}")
            # lookup share value at API to get price
            look_up = lookup(symbol)
            look_up_price = look_up['price']
            print(f"price:{look_up_price}")
            # value of sold shares - number sold * price each
            selling_cash = look_up_price * shares_to_sell
            print(f"selling_cash:{selling_cash}")
            if new_shares_amount < 0:
                ##FLASH MESSAGE
                print("Don't have that many shares")
                return render_template("sell.html", data=assets)
            else:
                # change share number in table
                db.execute("UPDATE assets SET shares=(:new_shares_amount) WHERE symbol=(:symbol) AND user_id=(:user_id)", new_shares_amount=new_shares_amount, user_id=user_id, symbol=symbol)
                # change total value - multiply remaining shares * price
                currentTotal = db.execute("SELECT total FROM assets WHERE  symbol=(:symbol) AND user_id=(:user_id)", user_id=user_id, symbol=symbol)
                new_total = new_shares_amount * look_up_price
                print(f"currentTotal:{currentTotal}")
                print('new_shares_amount * look_up_price = new_total')
                print(f"new_total: {new_total}")
                db.execute("UPDATE assets SET total=(:new_total) WHERE user_id=(:user_id) AND symbol=(:symbol)", new_total=new_total, user_id=user_id, symbol=symbol)
                # get current cash
                current_cash = db.execute("SELECT cash FROM users WHERE id=(:user_id)", user_id=user_id)
                current_cash = current_cash[0]['cash']
                print(f"current_cash: {current_cash}")
                # perform addition
                updated_cash = current_cash + selling_cash
                print(f"updated_cash:{updated_cash}")
                # update cash
                db.execute("UPDATE users SET cash=(:updated_cash) WHERE id=(:user_id)", updated_cash=updated_cash, user_id=user_id)
                return redirect(url_for("index"))

            return render_template("sell.html")
    return apology("TODO")


def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
