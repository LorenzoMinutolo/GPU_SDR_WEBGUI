import argparse
from app import db
from models import User
import getpass

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Test the basic VNA functionality.')

    parser.add_argument('--username', '-u', help='Name of the user', type=str, required=True)
    parser.add_argument('--email', '-m', help='Email of the user, optional', type=str, default = "")

    args = parser.parse_args()

    print("Adding User\n")
    print("Username:\t%s"%args.username)
    print("Email:\t%s"%args.email)
    u = User(username=args.username, email=args.email)
    password_is_set = False
    while not password_is_set:
        try:
            print("\nCreate password:")
            p = getpass.getpass()
            print("Repeat password:")
            pp = getpass.getpass()
            if p == pp:
                password_is_set = True
            else:
                print("the two strings don't match!")
        except Exception as error:
            print('ERROR', error)
        
    print("DONE!")
    u.set_password(p)
    db.session.add(u)
    db.session.commit()
