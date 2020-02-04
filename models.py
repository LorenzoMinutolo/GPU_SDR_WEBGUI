import re
from datetime import datetime
from app import app,db,u
from sqlalchemy.orm.exc import NoResultFound, StaleDataError, MultipleResultsFound
import os, glob
from werkzeug.security import generate_password_hash, check_password_hash
from search import add_to_index, remove_from_index, query_index
from flask_login import UserMixin
from app import login
from flask_login import current_user
from diagnostic_text import *
from multiprocessing import RLock, Manager

commit_manager = Manager()
commit_lock = commit_manager.RLock() # Recursive lock because db.session.commit() is a non-thread-safe operation

class User(UserMixin,db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<User {}>'.format(self.username)


@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class Measure(db.Model):
    __tablename__ = 'Measure'
    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(140))
    started_time = db.Column(db.String(140))
    relative_path = db.Column(db.String(200))
    comment = db.Column(db.String(300))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author = db.Column(db.Integer, db.ForeignKey('user.id'))
    plot = db.relationship('Plot', secondary="PlotVsMeasure", back_populates='measure') #, passive_deletes=True

    def get_plots(self):
        '''
        Get the plots in which this measure appears.

        Return:
            - The paths of the plots file in a list and the kind of the plot in an other list.

        Exammple:
        >>> path_list, kind_list = my_measure.get_plots()
        '''
        paths = []
        kinds = []
        timestamp = []
        comment = []
        for p in self.plot:
            paths.append(
                p.relative_path
            )
            kinds.append(
                p.kind
            )
            timestamp.append(
                str(p.timestamp)
            )
            comment.append(
                p.comment
            )
        return paths, kinds, timestamp, comment

    def __repr__(self):
        return '<Measure {}>'.format(self.id)

def filename_to_abs_path(filename):
    '''
    Return an error flag and eventually the complete path
    '''
    try:
        x = Measure.query.filter(Measure.relative_path.like("%"+os.path.basename(filename)+"%")).one()
        return False, os.path.join(app.config['GLOBAL_MEASURES_PATH'],x.relative_path)
    except NoResultFound:
        print_warning("No results found when converting file %s to relative path"%filename)
        return True, filename
    except MultipleResultsFound:
        print_warning("Multiple results found when converting file %s to relative path"%filename)
        return True, filename

def get_associated_plots(path_list):
    '''
    Given a list of paths returns a list of dictionaries containing {err:[boolean], plots[{ path:[], kind:[]}]}.
    Where the field err is true if a db query returns nothing (i.e. the measure is not registered in the database)
    '''
    ret = {
        'err':[],
        'plots':[]
    }
    for single_measure_path in path_list:
        current_plots = {
        }
        try:
            measure = Measure.query.filter(Measure.relative_path == single_measure_path).one()
            current_plots['path'],current_plots['kind'], current_plots['timestamp'], current_plots['comment'] = measure.get_plots()
            err = False
        except NoResultFound:
            current_plots['path'] = []
            current_plots['kind'] = []
            current_plots['timestamp'] = []
            current_plots['comment'] = []
            err = True

        ret['plots'].append(current_plots)
        ret['err'].append(err)

    return ret


def check_db_measure(path):
    '''
    Check if a measure actually exists in the database.
    '''
    try:
        measure = Measure.query.filter(Measure.relative_path == path).one()
        ret = True
    except NoResultFound:
        ret = False

    return ret


def add_measure_entry(relative_path, started_time, kind = "Unknown", comment = "", commit = True):
    '''
    Register a measure in the database.
    '''
    global commit_lock

    if current_user != None:
        author = current_user.username
    else:
        author = "TestEnv"
    m = Measure(
        relative_path = relative_path,
        started_time = started_time,
        kind = kind,
        comment = comment,
        author = author
    )
    db.session.add(m)
    if commit:
        commit_lock.acquire()
        db.session.commit()
        commit_lock.release()
    else:
        print_warning("Measure %s is waiting database commit"%relative_path)

class Plot(db.Model):
    __tablename__ = 'Plot'
    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(140))
    backend = db.Column(db.String(140))
    relative_path = db.Column(db.String(200))
    comment = db.Column(db.String(300))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author = db.Column(db.Integer, db.ForeignKey('user.id'))
    measure = db.relationship('Measure', secondary="PlotVsMeasure", back_populates='plot')

    def associate_files(self, file_paths):
        global commit_lock
        '''
        Associate the plot with multiple measures.

        Arguments
        '''
        if type(file_paths) == str:
            file_paths = [file_paths]
        for single_measure_path in file_paths:
            try:
                self.measure.append(
                    Measure.query.filter(Measure.relative_path == single_measure_path).one()
                )

            except NoResultFound:
                print_warning("No result found while associating %s with a measure db entry"% single_measure_path)

        commit_lock.acquire()
        db.session.commit()
        commit_lock.release()

    def get_sources(self):
        '''
        Get the source files of the plot.

        Return:
            - List of the path associated with the plot.
        '''
        ret = []
        for measure in self.measure:
            ret.append(
                measure.relative_path
            )
        return ret

    def __repr__(self):
        return '<Plot {}>'.format(self.id)

def add_plot_entry(relative_path, kind, backend, sources, comment = "", commit = True):
    '''
    Register a plot in the database.

    Arguments:
        - sources is a list of file paths or a string with a single file path
    '''
    global commit_lock
    if current_user != None:
        author = current_user.username
    else:
        author = "TestEnv"
    print(relative_path)
    p = Plot(
        relative_path = relative_path,
        kind = kind,
        backend = backend,
        comment = comment,
        author = author
    )
    db.session.add(p)
    p.associate_files(sources)
    if commit:
        commit_lock.acquire()
        db.session.commit()
        commit_lock.release()
    else:
        print_warning("plot %s is waiting for commit"%relative_path)

# Many to Many relationship bookeeping
PlotVsMeasure = db.Table('PlotVsMeasure',
    db.Column('id', db.Integer, primary_key=True),
    db.Column('measure_id', db.Integer, db.ForeignKey('Measure.id')),
    db.Column('plot_id', db.Integer, db.ForeignKey('Plot.id')),
    db.UniqueConstraint('measure_id', 'plot_id', name='unique_const')
)


def remove_measure_entry(rel_path):
    '''
    Remove a Measure entry from the database.
    '''
    global commit_lock

    try:
        commit_lock.acquire()
        x = Measure.query.filter(Measure.relative_path == rel_path).one()
        db.session.delete(x)
        db.session.commit()
        commit_lock.release()
        return True
    except NoResultFound:
        print_warning("Cannot find %s measure entry in the database")
        return False

def remove_plot_entry(rel_path):
    '''
    Remove a Plot entry from the database.
    '''
    global commit_lock

    try:
        commit_lock.acquire()
        db.session.delete(Plot.query.filter(Plot.relative_path == rel_path).one())
        db.session.commit()
        commit_lock.release()
        return True
    except NoResultFound:
        print_warning("Cannot find %s measure entry in the database")
        return False
    except StaleDataError:
        return False

def check_all_files():
    '''
    check the existance of all the files in the database, if the file do not exist, delete the reference
    '''
    print("Checking files in the database...")
    for m in Measure.query.all():
        try:
            full_path = app.config["GLOBAL_MEASURES_PATH"]  + (m.relative_path).strip("/")
            res = os.path.isfile(full_path)
        except AttributeError:
            res = False
        if not res:
            print_warning("%s does not exist, removing..."%(m.relative_path))
            ret = remove_measure_entry(m.relative_path)
            if not ret:
                print_error("Something went wrong in database logic.")


def check_all_plots():
    '''
    check the existance of all the plots in the database, if the file do not exist, delete the reference
    '''
    print("Checking plot files in the database...")
    for p in Plot.query.all():
        try:
            full_path = app.config["GLOBAL_MEASURES_PATH"]  + (p.relative_path).strip("/")
            res = os.path.isfile(full_path)
        except AttributeError:
            res = False
        if not res:
            print_warning("%s does not exist, removing..."%(p.relative_path))
            ret = remove_plot_entry(p.relative_path)
            if not ret:
                print_error("Something went wrong in database logic")

def measure_path_from_name(name):
    '''
    Return the measure path from the file name. If multiple path found or no path found raise ValueError.
    '''
    try:
        return Measure.query.filter(Measure.relative_path.like("%" + name + "%")).one().relative_path
    except NoResultFound:
        raise ValueError("Cannot convert name to path as no results from query")
    except MultipleResultsFound:
        raise ValueError("Cannot convert name to path as multiple results from query")


def patch_measure_from_path(rel_path, verbose = True):
    '''
    Given a measure not in the database try to find an item with the same filename and correct the relative path attribute; if no item is found, add a new item to the database.
    Return True if the match is succesfull, False if a new entry is created.
    '''
    global commit_lock

    if verbose: print("Trying to match %s file with the database..."%os.path.basename(rel_path))
    try:
        commit_lock.acquire()
        x = Measure.query.filter(Measure.relative_path.like("%"+os.path.basename(rel_path) + "%")).one()
        x.relative_path = rel_path
        ret = True
        db.session.commit()
        commit_lock.release()
    except NoResultFound:
        if verbose: print("No result found, creating new entry...")
        add_measure_entry(
            rel_path,
            datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
            kind = u.get_meas_type(os.path.relpath(app.config["GLOBAL_MEASURES_PATH"] + rel_path, os.getcwd()))[0],
            comment = "From auto patch",
            commit = True
        )
        ret = False

    return ret

def filename_from_plot_name(full_path):
    '''
    Recover the measure filename from a plot file. Requires the plot file to be named programmatically.
    '''

    # Because regular expression are cool
    tag = re.findall("\d{8}_\d{6}",os.path.basename(full_path))
    if tag:
        tag = tag[0]
    else:
        return ''
    try:
        x = Measure.query.filter(Measure.relative_path.like("%"+tag+"%")).one()
        return x.relative_path
    except NoResultFound:
        print_warning("Cannot return filename from plot tag \'%s\', skipping"%tag)
        return ''



def patch_plot_from_path(rel_path, verbose = True):
    '''
    Given a plot not in the database try to find an item with the same filename and correct the relative path attribute; if no item is found, add a new item to the database.
    Return True if the match is succesfull, False if a new entry is created.
    '''
    global commit_lock

    if verbose: print("Trying to match %s file with the database..."%os.path.basename(rel_path))
    try:
        commit_lock.acquire()
        x = Plot.query.filter(Plot.relative_path.like("%"+os.path.basename(rel_path) + "%")).one()
        x.relative_path = rel_path
        ret = True
        db.session.commit()
        commit_lock.release()
    except NoResultFound:
        #determine kind
        if os.path.basename(rel_path).find("Compare") >= 0:
            kind = 'multi'
        elif os.path.basename(rel_path).find("comapre") >= 0:
            kind = 'multi'
        else:
            kind = 'single'

        #determine backend
        if os.path.basename(rel_path).endswith('.png'):
            backend = 'matplotlib'
        elif os.path.basename(rel_path).endswith('.html'):
            backend = 'plotly'
        else:
            backend = 'unknown'

        #determine file association
        filename = filename_from_plot_name(rel_path)

        if len(filename) < 15:
            ret = False
        else:
            if verbose: print("No result found, creating new entry...")
            add_plot_entry(
                relative_path = rel_path,
                kind = kind,
                backend = backend,
                sources = filename,
                comment = "From auto patch",
                commit = True
            )
            ret = False

    return ret

def get_h5_files_from_root():
    '''
    Scan the root data folder and returns a list of relative paths for the measurements.
    '''
    ret = []
    for root, dirs, files in os.walk(app.config["GLOBAL_MEASURES_PATH"], topdown=False):
        for name in files:
            if name.endswith('.h5'):
                ret.append(os.path.join(os.path.relpath(root,app.config["GLOBAL_MEASURES_PATH"]), name))
    return ret

def get_plots_files_from_root():
    '''
    Scan the root data folder and returns a list of relative paths for the plots, and a list of for the backend.
    '''
    ret = []
    backend = []
    for root, dirs, files in os.walk(app.config["GLOBAL_MEASURES_PATH"], topdown=False):
        for name in files:
            if name.endswith('.png'):
                ret.append(os.path.join(os.path.relpath(root,app.config["GLOBAL_MEASURES_PATH"]), name))
                backend.append('matplotlib')
            elif name.endswith('.html'):
                ret.append(os.path.join(os.path.relpath(root,app.config["GLOBAL_MEASURES_PATH"]), name))
                backend.append('plotly')

    return ret, backend

def patch_measure_from_db(rel_path_from_Measure):
    '''
    Given a faulty db measure item (file in relative path is not there), scan the measure folder and tries to find it and correct the relative path.
    '''
    global commit_lock

    all_paths = get_h5_files_from_root()
    all_files = [os.path.basename(rel_path) for rel_path in all_paths]
    try:
        x = Measure.query.filter(Measure.relative_path == rel_path_from_Measure).one()
        try:
            commit_lock.acquire()
            target_path = all_files.index(os.path.basename(x.relative_path))
            x.relative_path = all_paths[target_path]
            db.session.commit()
            commit_lock.release()
            return True
        except ValueError:
            print_warning("Cannot find db item %s in current file structure"%os.path.basename(x.relative_path))
            return False
    except MultipleResultsFound:
        print_warning("Cannot patch the file %s as multiple result were found. Decoupling requires additional implementation."%os.path.basename(x.relative_path))
        return False
    except NoResultFound:
        print_error("Cannot find the database item corresponding to path %s, cannot repair"%rel_path_from_Measure)
        return False

def patch_plot_from_db(rel_path_from_Plot):
    '''
    Given a faulty db plot item (file in relative path is not there), scan the measure folder and tries to find it and correct the relative path.
    '''
    global commit_lock
    all_paths, backends = get_plots_files_from_root()
    all_files = [os.path.basename(rel_path) for rel_path in all_paths]
    try:
        x = Plot.query.filter(Plot.relative_path == rel_path_from_Plot).one()
        try:
            commit_lock.acquire()
            target_path = all_files.index(os.path.basename(x.relative_path))
            x.relative_path = all_paths[target_path]
            db.session.commit()
            commit_lock.release()
            return True
        except ValueError:
            print_warning("Cannot find db item %s in current file structure"%os.path.basename(x.relative_path))
            return False
    except MultipleResultsFound:
        print_warning("Cannot patch the file %s as multiple result were found. Decoupling requires additional implementation."%os.path.basename(x.relative_path))
        return False
    except NoResultFound:
        print_error("Cannot find the database item corresponding to path %s, cannot repair"%rel_path_from_Plot)
        return False

def rebuild_measure_database():
    '''
    Analyze the current measure path and rebuild a database.
    '''

    h5files = get_h5_files_from_root()
    for fp in h5files:
        patch_measure_from_path(fp, verbose = True)


def rebuild_plot_database():
    '''
    Try to rebuild the database of the plots. Compare plots are not accounted.
    This function is based on nomenclature and require the plots to not have custom names and the measure database to be compiled.
    '''

    plots, kinds = get_plots_files_from_root()
    for fp in plots:
        patch_plot_from_path(fp, verbose = True)

# Temporary file select, was too big for cookies.
# This table is not associated with the database directly, I don't see the point at this stage
class Tmp_files(db.Model):
    __tablename__ = 'Tmp_files'
    id = db.Column(db.Integer, primary_key=True)
    measure = db.Column(db.String(140))
    user = db.Column(db.String(140))
    def __repr__(self):
        return '<tmp_file {}>'.format(self.id)

def add_file_selected(path):
    '''
    Add a file to temporary list
    '''
    global commit_lock
    if current_user != None:
        author = current_user.username
    else:
        author = "TestEnv"

    try:
        Tmp_files.query.filter(Tmp_files.measure==path).filter(Tmp_files.user==author).one()
    except NoResultFound:
        m = Tmp_files(measure = path, user = author)

        commit_lock.acquire()
        db.session.add(m)
        db.session.commit()
        commit_lock.release()
        return True
    else:
        print_warning("Cannot add %s, on tmp files of user %s. Already present"%(path,author))
        return False

def remove_file_selected(path):
    '''
    Remove selected file
    '''
    global commit_lock

    try:
        x = Tmp_files.query.filter(Tmp_files.measure==path).one()
    except NoResultFound:
        print_warning("Cannot remove temporary measure as it's not there")
    except MultipleResultsFound:
        print_warning("Cannot remove temporary measure as there are multiple with the same path")
    else:
        commit_lock.acquire()
        db.session.delete(x)
        db.session.commit()
        commit_lock.release()
        return True
    return False

def clear_all_files_selected():
    '''
    Clear the selection table
    '''
    global commit_lock
    print("Clearing all temporary file selection...")
    list_x = Tmp_files.query.all()

    commit_lock.acquire()
    for x in list_x:
        db.session.delete(x)

    db.session.commit()
    commit_lock.release()

def clear_user_file_selected():
    '''
    Clear the file selected for a single user
    '''
    global commit_lock

    if current_user != None:
        author = current_user.username
    else:
        author = "TestEnv"
    print("Clearing all temporary file selection dor use %s..."%author)
    list_x = Tmp_files.query.filter(Tmp_files.user==author).all()

    commit_lock.acquire()
    for x in list_x:
        db.session.delete(x)

    db.session.commit()
    commit_lock.release()

def user_files_selected():
    '''
    Return a list of strings with the filename selected
    '''
    global commit_lock
    if current_user != None:
        author = current_user.username
    else:
        author = "TestEnv"
    commit_lock.acquire()
    list_x = Tmp_files.query.filter(Tmp_files.user==author).all()
    commit_lock.release()
    ret = []
    for x in list_x:
        ret.append(
            x.measure
        )
    return ret

# Source file select, was too big for cookies.
# This table is not associated with the database directly, I don't see the point at this stage
class Source_files(db.Model):
    __tablename__ = 'Source_files'
    id = db.Column(db.Integer, primary_key=True)
    measure = db.Column(db.String(140))
    user = db.Column(db.String(140))
    kind = db.Column(db.String(140))
    group = db.Column(db.String(140), default='general')
    permanent = db.Column(db.Boolean, default=False) # avoid deletion over restart of the application
    def __repr__(self):
        return '<source_file {}>'.format(self.id)

def add_file_source(path, permanent, group = None):
    '''
    Add a file to source file list
    '''
    global commit_lock
    if group is None:
        group = 'general'
    if current_user != None:
        author = current_user.username
    else:
        author = "TestEnv"
    if path.endswith('.h5'):
        try:
            Source_files.query.filter(Source_files.measure==path).filter(Source_files.user==author).one()
        except NoResultFound:
            kind = u.get_meas_type(os.path.relpath(app.config["GLOBAL_MEASURES_PATH"] + path, os.getcwd()))[0]
            m = Source_files(measure = path, user = author, permanent = permanent, group = group, kind = kind)

            commit_lock.acquire()
            db.session.add(m)
            db.session.commit()
            commit_lock.release()
            return True
        else:
            print_warning("Cannot add %s, on source files of user %s. Already present"%(path,author))
            return False
    else:
        ret = True
        abs_path = os.path.join(os.path.relpath(app.config["GLOBAL_MEASURES_PATH"] + path, os.getcwd()),"*.h5")
        print(abs_path)
        if len(glob.glob(abs_path))!=0:
            for f in glob.glob(abs_path):
                print(f)
                meas_name =os.path.join(path,os.path.basename(f))
                try:
                    Source_files.query.filter(Source_files.measure==meas_name).filter(Source_files.user==author).one()
                except NoResultFound:
                    kind = u.get_meas_type(f)[0]
                    m = Source_files(measure = meas_name, user = author, permanent = permanent, group = group, kind = kind)

                    commit_lock.acquire()
                    db.session.add(m)
                    db.session.commit()
                    commit_lock.release()

                else:
                    print_warning("Cannot add %s, on source files of user %s. Already present"%(sub_path,author))
                    ret = False
            return ret
        else:
            print_warning("Cannot add %s, on source files of user %s. No file present"%(path,author))
            return False

def remove_file_source(path):
    '''
    Remove source file
    '''
    global commit_lock

    try:
        x = Source_files.query.filter(Source_files.measure==path).one()
        if x.permanent:
            print_warning("removing permanent source file")
    except NoResultFound:
        print_warning("Cannot remove temporary measure as it's not there")
    except MultipleResultsFound:
        print_warning("Cannot remove temporary measure as there are multiple with the same path")
    else:
        commit_lock.acquire()
        db.session.delete(x)
        db.session.commit()
        commit_lock.release()
        return True
    return False


def remove_source_group(group):
    '''
    Remove all measures in a source group.
    '''
    global commit_lock
    print_warning("Cleaning source file group %s"%group)
    commit_lock.acquire()
    q_results = Source_files.query.filter(Source_files.group==group).all()
    for q in q_results:
        db.session.delete(q)
    db.session.commit()
    commit_lock.release()

def consolidate_sources():
    '''
    Make sure that all measures in the source file table are present for the current user.
    '''
    global commit_lock
    print_warning("Consolidating all source files for user %s..."%current_user.username)
    commit_lock.acquire()
    q_results = Source_files.query.filter(Source_files.user == current_user.username).all()
    res = []
    for q in q_results:
        try:
            Measure.query.filter(Measure.relative_path == q.measure).one()
        except NoResultFound:
            print_warning("Source file %s has not been found in the measures database, removing..")
            res.append(q.measure)
            db.session.delete(q)
        except MultipleResultsFound:
            print_warning("Source file %s has has been linked to multiple measures database, removing..")
            res.append(q.measure)
            db.session.delete(q)
        else:
            print("Source file %s is ok"%q.measure)
    return res


    db.session.commit()
    commit_lock.release()

def clear_all_files_source(permanent = False):
    '''
    Clear the source file table
    '''
    global commit_lock
    print("Clearing all temporary file selection...")
    if permanent:
        list_x = Source_files.query.all()
    else:
        list_x = Source_files.query.filter(Source_files.permanent == False).all()

    commit_lock.acquire()
    for x in list_x:
        db.session.delete(x)

    db.session.commit()
    commit_lock.release()

def clear_user_file_source(permanent = False):
    '''
    Clear the file selected for a single user
    '''
    global commit_lock

    if current_user != None:
        author = current_user.username
    else:
        author = "TestEnv"
    if permanent:
        print_warning("Clearing all temporary file selection dor use %s..."%author)
        list_x = Source_files.query.filter(Source_files.user==author).all()
    else:
        list_x = Source_files.query.filter(Source_files.user==author).filter(Source_files.permanent == False).all()
    commit_lock.acquire()
    for x in list_x:
        db.session.delete(x)

    db.session.commit()
    commit_lock.release()

def user_files_source(group = None):
    '''
    Return a list of strings with the filename selected
    '''
    global commit_lock
    if current_user != None:
        author = current_user.username
    else:
        author = "TestEnv"
    commit_lock.acquire()
    if group is None:
        list_x = Source_files.query.filter(Source_files.user==author).all()
    else:
        list_x = Source_files.query.filter(Source_files.user==author).filter(Source_files.group==group).all()
    commit_lock.release()
    path = []
    kind = []
    perm = []
    group = []
    for x in list_x:
        path.append(x.measure)
        kind.append(x.kind)
        perm.append(x.permanent)
        group.append(x.group)
    return path, kind, perm, group
