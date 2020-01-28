from datetime import datetime
from app import app,db
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
        for p in self.plot:
            paths.append(
                p.relative_path
            )
            kinds.append(
                p.kind
            )
        return paths, kinds
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
            'path':[],
            'kind':[]
        }
        try:
            measure = Measure.query.filter(Measure.relative_path == single_measure_path).one()
            current_plots['path'],current_plots['kind'] = measure.get_plots()
            err = False
        except NoResultFound:
            err = True

        ret['plots'].append(current_plots)
        ret['plots'].append(current_plots)

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
                print_warning("No result found while associating %s with a plot"% single_measure_path)

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


def rebuild_measure_database():
    '''
    Analyze the current measure path and rebuild a database.
    '''
    pass

def rebuild_plot_database():
    '''
    Try to rebuild the database of the plots. Compare plots are not accounted.
    This function is based on nomenclature and require the plots to not have custom names and the measure database to be compiled.
    '''
