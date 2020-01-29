import re
from datetime import datetime
from app import app,db,u
from sqlalchemy.orm.exc import NoResultFound, StaleDataError, MultipleResultsFound
import os
from werkzeug.security import generate_password_hash, check_password_hash
from search import add_to_index, remove_from_index, query_index
from flask_login import UserMixin
from app import login
from flask_login import current_user
from diagnostic_text import *

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


def add_measure_entry(relative_path, started_time, kind = "Unknown", comment = "", commit = True):
    '''
    Register a measure in the database.
    '''
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
        db.session.commit()
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

        db.session.commit()

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
        db.session.commit()
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
    try:
        x = Measure.query.filter(Measure.relative_path == rel_path).one()
        db.session.delete(x)
        db.session.commit()
        return True
    except NoResultFound:
        print_warning("Cannot find %s measure entry in the database")
        return False

def remove_plot_entry(rel_path):
    '''
    Remove a Plot entry from the database.
    '''
    try:
        db.session.delete(Plot.query.filter(Plot.relative_path == rel_path).one())
        db.session.commit()
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


def patch_measure_from_path(rel_path, verbose = True):
    '''
    Given a measure not in the database try to find an item with the same filename and correct the relative path attribute; if no item is found, add a new item to the database.
    Return True if the match is succesfull, False if a new entry is created.
    '''
    if verbose: print("Trying to match %s file with the database..."%os.path.basename(rel_path))
    try:
        x = Measure.query.filter(Measure.relative_path.like("%"+os.path.basename(rel_path) + "%")).one()
        x.relative_path = rel_path
        ret = True
        db.session.commit()
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
    if verbose: print("Trying to match %s file with the database..."%os.path.basename(rel_path))
    try:
        x = Plot.query.filter(Plot.relative_path.like("%"+os.path.basename(rel_path) + "%")).one()
        x.relative_path = rel_path
        ret = True
        db.session.commit()
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
    all_paths = get_h5_files_from_root()
    all_files = [os.path.basename(rel_path) for rel_path in all_paths]
    try:
        x = Measure.query.filter(Measure.relative_path == rel_path_from_Measure).one()
        try:
            target_path = all_files.index(os.path.basename(x.relative_path))
            x.relative_path = all_paths[target_path]
            db.session.commit()
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
    all_paths, backends = get_plots_files_from_root()
    all_files = [os.path.basename(rel_path) for rel_path in all_paths]
    try:
        x = Plot.query.filter(Plot.relative_path == rel_path_from_Plot).one()
        try:
            target_path = all_files.index(os.path.basename(x.relative_path))
            x.relative_path = all_paths[target_path]
            db.session.commit()
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
