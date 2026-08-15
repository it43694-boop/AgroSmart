import sys, pathlib


def main():
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
    from database import SessionLocal
    from models import FinanceRecord, User
    import auth, requests, json

    db = SessionLocal()
    rec = db.query(FinanceRecord).filter(FinanceRecord.id == 2).first()
    if not rec:
        print('no record id=2')
        db.close()
        sys.exit(1)

    user = db.query(User).filter(User.id == rec.owner_id).first()
    print('record', rec.id, rec.revenue, rec.cost, 'owner', user.id, user.email)
    # create token
    token = auth.create_access_token({'sub': user.email})
    print('token len', len(token))
    headers = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
    resp = requests.patch(
        f'http://127.0.0.1:8001/users/{user.id}/finance/{rec.id}',
        headers=headers,
        json={'revenue': 111.11, 'cost': 22.22},
        timeout=10
    )
    print('status', resp.status_code)
    print(resp.text)

    db.close()


if __name__ == "__main__":
    main()
