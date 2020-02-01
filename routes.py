from flask import render_template,flash, redirect,url_for,render_template_string,send_from_directory
from app import app,db,job_manager
from forms import LoginForm, JustAPlaceholder, SearchForm,RegistrationForm
from flask_login import current_user, login_user
from models import User, Plot, get_associated_plots
from flask_login import login_required
from flask import request, jsonify
from werkzeug.urls import url_parse
from flask_login import logout_user
from datetime import datetime
import glob,os
import json
from flask import g
import ntpath
from models import user_files_selected
from app import u, check_connection


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        g.search_form = SearchForm()

@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    worker_status = job_manager.workers_status()
    return render_template(
        'index.html',
        title='Home',
        workers = worker_status,
        worker_range = range(len(worker_status['name']))
    )


@app.route('/index_about')
@login_required
def index_about():
    return render_template('index_about.html', title='About')

@app.route('/connections', methods=['GET', 'POST'])
@login_required
def connections():
    return render_template('connections.html', title='manage_connections',
        binary_connected = int(check_connection()),
        usrp_prop = [{'name': 'usrp_name', 'serial':'XCNN345'}],
        dcard_prop = [{'name':'wbx-fake','range':'100 MHz - 6 GHz'},{'name':'wbx-fake','range':'100 MHz - 6 GHz'}],
        gpu_prop = [{'name':'gtx2070 max-q','cuda_cores':1236},{'name':'gtx2070 max-q','cuda_cores':1236}],
    )

@app.route('/index_help')
@login_required
def index_help():
    return render_template('index_help.html', title='About')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
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
        login_user(user, remember=form.remember_me.data)
        return redirect(url_for('index'))
    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
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

@app.route('/user/<username>')
@login_required
def user(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    sessions = Session.query.filter_by(author = user).order_by(Session.timestamp.desc()).paginate(page, app.config["SESSIONS_PER_PAGE"], False)
    next_url = url_for('index', page=sessions.next_num) \
        if sessions.has_next else None
    prev_url = url_for('index', page=sessions.prev_num) \
        if sessions.has_prev else None
    return render_template('user.html', user=user, sessions=sessions.items,next_url=next_url, prev_url=prev_url)

@login_required
@app.route('/session', methods=['GET', 'POST'])
def x_session():
    form = JustAPlaceholder()
    if form.validate_on_submit():
        session = Session(body=form.session.data, author=current_user)
        db.session.add(session)
        db.session.commit()
        flash('Measurement session added!')
        return redirect(url_for('index'))
    return render_template('session.html', title='Session', form=form)

@login_required
@app.route('/measure_vna', methods=['GET', 'POST'])
def measure_vna(script = None):
    return render_template('measure_vna.html', title='VNA')


def what_kind(filename):
    meas_type = u.get_meas_type(filename)[0] ## TODO: for now just returns the first meas type
    return meas_type

def what_size(filename):
    filesize_MB = os.path.getsize(filename) >> 20
    if filesize_MB >= 1000:
        return "%.1f GB"%(filesize_MB/1000.)
    elif filesize_MB < 1:
        return "< 1 MB"
    else:
        return "%.1f MB"%(filesize_MB)

def scanfiles(current_path):
    '''
    This function has to be modified, is quite messy due to multiple iterations
    '''
    files = []
    sizes = []
    for file in glob.glob(current_path+"*.h5"):
        files.append(str(file))
        sizes.append(str(os.stat(str(file)).st_size))
    f = [ntpath.basename(c) for c in files]
    p = []
    k = []
    s = []
    for i in files:
        head, tail = ntpath.split(i)
        head = os.path.relpath(head,current_path)
        p.append(head)
        k.append(what_kind(i))
        s.append(what_size(i))

    return p,f,s,k

def scanfolders(path):
    folder_names = next(os.walk(path))[1]
    h5num = []

    for folder_name in folder_names:
        #h5num.append(len(scanfiles(path+folder_name+"/")[0]))
        h5num.append(len([files_h5 for root_, dirs_, files_ in os.walk(path+folder_name) for files_h5 in files_ if files_h5.endswith(".h5")]))
        #h5num.append( sum([len(files) for r, d, files in os.walk(path+folder_name)]))
    if isinstance(folder_names, str):
        folder_names = [folder_names]
    return folder_names,h5num


def check_path(current_path):

    if not os.path.isdir(current_path):
        msg = "the path %s is non existent,"%current_path
        raise KeyError(msg)
        ### SHOULD RETURN A HTTP MESSAGE ISNSTEAD TODO#

@app.route('/explore_help', methods=['GET', 'POST'])
@login_required
def explore_help():
    return render_template('explore_help.html', title='Explore_help')

@app.route('/explore_all', methods=['GET', 'POST'])
@login_required
def explore_all():
    current_path = app.config['GLOBAL_MEASURES_PATH']
    check_path(current_path)
    if request.method == 'POST':
        if request.form.get('submit_button') == 'Set path':
            current_path = request.form['req_path']
            ### HUGE SECURYTY ISSUE TODO TODO###

    elif request.method == 'GET':
        pass
    paths, files, sizes, kinds = scanfiles(current_path)
    return render_template('explore_all.html', title='Explore_all', allfiles = list(zip(files, paths, sizes, kinds)), current_meas_path = current_path)


@app.route('/explore', methods=['GET', 'POST'])
@app.route('/explore/<path:path>', methods=['GET', 'POST'])
@login_required
def explore(path = ""):
    #current_session.clear()
    #current_session['selected_paths'] = [1,2,3]
    current_path = os.path.join(app.config['GLOBAL_MEASURES_PATH'], path)
    request_error = {'enable':False, 'message':None}
    if path.endswith(".png"):
        print('file requested: %s'%path)
        return send_from_directory(directory=os.path.dirname(current_path), filename=os.path.basename(path))
    elif path.endswith(".html"):
        print('file requested: %s'%path)
        return send_from_directory(directory=os.path.dirname(current_path), filename=os.path.basename(path))
    else:
        folder_to_scan = []
        if request.method == 'POST':
            if request.form.get('select_button') == 'Show files >>':
                folder_to_scan = request.form.getlist('folders')
            else:
                file_list = request.form.getlist('files_selected')
                if len(file_list)>0:
                    print("Working on files: "+str(file_list))
                    if request.form.get('plot_button') == 'Plot':
                        request_error['enable'] = True
                        request_error['message'] = str(file_list)
                    if request.form.get('analyze_button') == 'Analyze':
                        request_error['enable'] = True
                        request_error['message'] = "Analysis not developed"
                    if request.form.get('export_button') == 'Export':
                        request_error['enable'] = True
                        request_error['message'] = "Export not developed"
                    if request.form.get('export_source') == 'Use as source':
                        request_error['enable'] = True
                        request_error['message'] = "Source not developed"
                else:
                    request_error['enable'] = True
                    request_error['message'] = "No File selected"

        elif request.method == 'GET':
            pass

        #do not change directory, this is a limitation
        folder_names, h5num = scanfolders(current_path)

        if len(folder_to_scan) == 0:
            paths, files, sizes, kinds = scanfiles(current_path)
        else:
            paths = []
            files = []
            sizes =[]
            kinds = []

            for ff in folder_to_scan:
                paths_, files_, sizes_, kinds_ = scanfiles(current_path+ff+"/")
                paths.extend(paths_)
                files.extend(files_)
                sizes.extend(sizes_)
                kinds.extend(kinds_)

        f_checked = []
        for i in range(len(folder_names)):
            if folder_names[i] in folder_to_scan:
                f_checked.append( True)
            else:
                f_checked.append(False)


        full_paths_list = [os.path.join(path,x) for x in files]
        measure_link = get_associated_plots(full_paths_list)
        #print(measure_link)
        return render_template('explore.html', title='Explore',
            allfiles = list(zip(files, paths, sizes, kinds)),
            measure_link = measure_link,
            allfolders = list(zip(folder_names, h5num, f_checked)),
            err = request_error,
            current_path = url_for("explore")+"/"+path,
            visual_path = path.split("/")[:-1],
            simple_path = path,
            selected_files = user_files_selected()
            )
#style="width: auto !important; display: inline-block; max-width: 100%;"
#style="display: flex !important; justify-content: center; align-items: center;"
@login_required
@app.route('/show_plot', methods=['GET', 'POST'])
def show_plot():
    return render_template('example_load.html')

@app.route('/add_numbers')
def add_numbers():
    a = request.args.get('a', 0, type=int)
    b = request.args.get('b', 0, type=int)
    return jsonify(result=a + b)

@app.route('/a')
def test():
    return render_template('a.html')

@app.route('/search')
@login_required
def search():
    if g.search_form.validate():
        page = request.args.get('page', 1, type=int)
        sessions = Session.query.filter(Session.body.contains(g.search_form.q.data)).paginate(page, app.config["SESSIONS_PER_PAGE"], False)
        next_url = url_for('index', page=sessions.next_num) \
            if sessions.has_next else None
        prev_url = url_for('index', page=sessions.prev_num) \
            if sessions.has_prev else None
        return render_template('search.html', title=('Search'), sessions=sessions.items,next_url=next_url, prev_url=prev_url)
