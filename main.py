from __future__             import print_function
from flask                  import Flask, render_template, request, send_from_directory, make_response ,session as login_session, jsonify, flash, redirect
from dataBase_setup         import User, Category, Item, session__
from oauth2client.client    import flow_from_clientsecrets, FlowExchangeError

import random
import string
import httplib2
import json
import sys
import requests

CLIENT_ID = json.loads(open('client_secrets.json','r').read())['web']['client_id']

app = Flask(__name__)
app.secret_key = 'private'


@app.route('/', methods=['GET'])
def index():
    try:
        login_session['logged']
    except Exception as err:
        login_session['logged'] = None
    categories_ = [category[0] for category in session__.query(Category.name).all()]
    some_items = [item[0] for item in session__.query(Item.name).limit(19).all()]
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
    login_session['state'] = state
    return render_template('index.html', categories=categories_, items=some_items, logged=login_session['logged'],STATE=state)


@app.route('/category/<path:category>')
def get_category(category):
    categories_ = [category[0] for category in session__.query(Category.name).all()]
    category_id = session__.query(Category.id).filter(Category.name == category).one()[0]

    items_for_category = [item[0] for item in session__.query(Item.name).filter(Item.category_id == category_id).all()]
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
    login_session['state'] = state
    return render_template('index.html', categories=categories_, items=items_for_category,
                           logged=login_session['logged'],STATE=state)


@app.route('/item/<path:item>')
def show_item_details(item):
    item_object = session__.query(Item.name, Item.description).filter(Item.name == item).one()
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
    login_session['state'] = state
    return render_template('item_details.html', item_details=item_object[1], item=item,
                           logged=login_session['logged'],STATE=state)


@app.route('/delete/item/<path:item>')
def delete_item(item):
    if login_session['logged'] == True:
        item_object = session__.query(Item).filter(Item.name == item).one()
        if item_object.user_id == login_session['userid']:
            session__.delete(item_object)
            session__.commit()
            flash("item deleted successfully","success")
        else:
            flash("you are not allowed to delete this item","error")
    return redirect('/')

@app.route('/edit/item/<path:item>', methods=['GET'])
def edit_item(item):
    if login_session['logged'] == True:
        item_object = session__.query(Item.name, Item.description, Item.category_id, Item.user_id,Item.id).filter(Item.name == item).first()
        if item_object[3]== login_session['userid']:
            category_name = session__.query(Category.name).filter(Category.id == item_object[2]).first()[0]
            item_object = [item_object[0], item_object[1], category_name, item_object[4]]
            allCats_ = session__.query(Category).all()
            allCats = []
            for cat in allCats_:
                cat_ = {}
                cat_['id'] = cat.id
                cat_['name'] = cat.name
                allCats.append(cat_)
            return render_template('edit_item.html', item=item_object, logged=login_session['logged'], Categories = allCats)
        else:
            flash("you don't have permission to edit this item","error")
            return redirect('/')
    else:
        flash("you must login first","error")
        return redirect('/')


@app.route('/edit/item', methods=['POST'])
def submit_edit_item():
    title = request.form['txtTitle']
    description = request.form['txtDescription']
    category = request.form['ddCategory']
    itemId = request.form['txtId']

    session__.query(Item).filter(Item.id == itemId).update(
        {"name": title, "description": description, "category_id": category})
    flash("item editted successfullt","success")

    return redirect('/')

@app.route('/gconnect', methods=['POST'])
def gconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps("invalid state parameter"),401)
        response.headers['Content-Type'] = 'application/json'
        return response

    code = request.data
    try:
        oauth_flow = flow_from_clientsecrets("client_secrets.json",scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(json.dumps("failed to upgrade the authorization code"),401)
        response.headers['Content-Type'] = 'application/json'
        return response

    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])

    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')),500)
        response.headers['Content-Type'] = 'application/json'
        return response

    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(json.dumps("token's user id doesn't match gicen user id"),401)
        response.headers['Content-Type'] = 'application/json'
        return response

    if result['issued_to'] != CLIENT_ID:
        response = make_response(json.dumps("token's client id  doesn't match"),401)
        response.headers['Content-Type'] = 'application/json'
        #print "token's client id doesn't match app's"
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps("Current user is already connected"),200)
        response.headers['Content-Type'] = 'application/json'
        return response

    login_session['credentials'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt':'json'}
    answer = requests.get(userinfo_url, params=params)
    data = json.loads(answer.text)
    print(data,file=sys.stderr)
    checkEmail = session__.query(User.email,User.id).filter(User.email==data['email']).first()
    if checkEmail == None:
        newUser = User()
        newUser.email = data['email']
        newUser.name = data['name']
        session__.add(newUser)
        session__.commit()
        login_session['userid'] = newUser.id
    else:
        print(checkEmail, file=sys.stderr)
        login_session['userid'] = checkEmail[1]
    login_session['username'] = data['name']
    login_session['email'] = data['email']
    login_session['logged'] = True
    return ("welcome %s" %login_session['username'])





@app.route('/logout')
def submit_logout():
    if login_session['logged']:
        login_session['logged'] = None
        login_session['credentials'] = None
        login_session['gplus_id'] = None
        login_session['username'] = None
        login_session['userid'] = None
        login_session['email'] = None

    return redirect('/')


@app.route('/statics/<path:path>')
def send_js(path):
    return send_from_directory('statics', path)


@app.route('/catalog.json')
def jsons():
    data = {}
    categories_ = [category[0] for category in session__.query(Category.name).all()]
    for category in categories_:
        data[category] = []
        category_id = session__.query(Category.id).filter(Category.name == category).first()[0]
        for item in session__.query(Item.name, Item.description).filter(Item.category_id == category_id).all():
            data[category].append({
                "name": item[0],
                "description": item[1]
            })
    return jsonify(data)

@app.route('/add/item', methods=['GET','POST'])
def addItem():
    if login_session['logged'] is not None:
        if request.method == 'POST':
            txtItemName = request.form['txtItemName']
            txtItemDesc = request.form['txtItemDesc']
            ddItemCat = request.form['ddItemCategory']
            newItem = Item()
            newItem.name = txtItemName
            newItem.description = txtItemDesc
            newItem.category_id = ddItemCat
            newItem.user_id = login_session['userid']
            session__.add(newItem)
            session__.commit()
            flash("new item added successfully","success")
            return redirect('/')
        allCats_ = session__.query(Category).all()
        allCats = []
        for cat in allCats_:
            cat_ = {}
            cat_['id'] = cat.id
            cat_['name'] = cat.name
            allCats.append(cat_)
        #print(allCats,file=sys.stderr)
        return render_template('add_item.html',Categories = allCats)
    else:
        flash("you must login first!","error")
        return redirect('/')

@app.route('/add/category', methods=['GET','POST'])
def addCategory():
    if login_session['logged'] is not None:
        if request.method == 'POST':
            cname = request.form['txtCategoryName']
            newCategory = Category()
            newCategory.name = cname
            session__.add(newCategory)
            session__.commit()
            flash('new category added successfully!','success')
            return redirect('/')
        return render_template('add_category.html',logged = login_session['logged'])
    else:
        flash('you must login first!','error')
        return redirect('/')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
