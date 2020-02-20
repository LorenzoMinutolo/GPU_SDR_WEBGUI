GPU SDR WEB-GUI
===============

Web-gui for the Python API of GPU SDR


Considerations
--------------

This is the first commit on GitHub. This project is almost undocumented and not functional at all at the moment.
If you wan to join the development consider contacting me via email.

Initialization
--------------

  * Go into app.py and change the GLOBAL_MEASURES_PATH variable pointing to a local existing path possibly containing some measure
  * ./initialize.sh
  * python add_user.py -u <your username>
  * python build_measure_db.py
  * Run the application using python app.run
  * Start testing the app navigating with a local browser to 0.0.0.0:5000
