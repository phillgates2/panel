#!/usr/bin/env python3
"""Create an admin user for the Panel application.

Usage:
  python scripts/create_admin.py --email admin@example.com --password secret

This script creates or updates a `User` with role `system_admin`.
"""
import argparse
from app import create_app, db, User


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--email', required=True)
    p.add_argument('--password', required=True)
    args = p.parse_args()

    app = create_app()
    with app.app_context():
        email = args.email.strip().lower()
        user = db.session.query(User).filter_by(email=email).first()
        if not user:
            # create a dummy user with minimal fields required by model
            from datetime import date
            user = User(first_name='Admin', last_name='', email=email, dob=date(1970,1,1))
            user.set_password(args.password)
            user.role = 'system_admin'
            db.session.add(user)
            db.session.commit()
            print('Created admin user:', email)
        else:
            user.set_password(args.password)
            user.role = 'system_admin'
            db.session.commit()
            print('Updated admin user password and role for:', email)


if __name__ == '__main__':
    main()
