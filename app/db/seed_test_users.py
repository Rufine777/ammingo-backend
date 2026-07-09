import base64
import os
import qrcode
from io import BytesIO
from app.db.db import SessionLocal
from app.db.models import User, Game, Bingo

# Predefined list of 27 test users
TEST_USERS = [
    {"name": "Alice", "username": "test_alice", "email": "test1@example.com", "code": "NWHB2V"},
    {"name": "Bob", "username": "test_bob", "email": "test2@example.com", "code": "KC51ZY"},
    {"name": "Charlie", "username": "test_charlie", "email": "test3@example.com", "code": "F1F0SP"},
    {"name": "David", "username": "test_david", "email": "test4@example.com", "code": "CL4HGC"},
    {"name": "Emma", "username": "test_emma", "email": "test5@example.com", "code": "ESGOHZ"},
    {"name": "Frank", "username": "test_frank", "email": "test6@example.com", "code": "5RIE9S"},
    {"name": "Grace", "username": "test_grace", "email": "test7@example.com", "code": "RIH6EN"},
    {"name": "Henry", "username": "test_henry", "email": "test8@example.com", "code": "T7BBCT"},
    {"name": "Ivy", "username": "test_ivy", "email": "test9@example.com", "code": "3TZP9A"},
    {"name": "Jack", "username": "test_jack", "email": "test10@example.com", "code": "9ZIZD1"},
    {"name": "Kevin", "username": "test_kevin", "email": "test11@example.com", "code": "RW7BWQ"},
    {"name": "Leo", "username": "test_leo", "email": "test12@example.com", "code": "XCSPDT"},
    {"name": "Mary", "username": "test_mary", "email": "test13@example.com", "code": "LQT39S"},
    {"name": "Nora", "username": "test_nora", "email": "test14@example.com", "code": "GL60LL"},
    {"name": "Oliver", "username": "test_oliver", "email": "test15@example.com", "code": "7WTGTN"},
    {"name": "Paul", "username": "test_paul", "email": "test16@example.com", "code": "70R2U1"},
    {"name": "Quinn", "username": "test_quinn", "email": "test17@example.com", "code": "L5E052"},
    {"name": "Rachel", "username": "test_rachel", "email": "test18@example.com", "code": "Q8B5M2"},
    {"name": "Sam", "username": "test_sam", "email": "test19@example.com", "code": "19B0X5"},
    {"name": "Tina", "username": "test_tina", "email": "test20@example.com", "code": "Z89P41"},
    {"name": "Uma", "username": "test_uma", "email": "test21@example.com", "code": "H4B7N1"},
    {"name": "Victor", "username": "test_victor", "email": "test22@example.com", "code": "V90K4M"},
    {"name": "Wendy", "username": "test_wendy", "email": "test23@example.com", "code": "W4B9K1"},
    {"name": "Xavier", "username": "test_xavier", "email": "test24@example.com", "code": "X92K4L"},
    {"name": "Yara", "username": "test_yara", "email": "test25@example.com", "code": "Y73L8K"},
    {"name": "Zach", "username": "test_zach", "email": "test26@example.com", "code": "Z01M9J"},
    {"name": "Zoe", "username": "test_zoe", "email": "test27@example.com", "code": "Z42P8T"}
]

def seed_users():
    db = SessionLocal()
    try:
        print("Seeding test users...")
        for u in TEST_USERS:
            # Check if user already exists
            user = db.query(User).filter(User.email == u["email"]).first()
            if not user:
                # Create QR Code for user profile
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(u["code"])
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                qr_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

                new_user = User(
                    name=u["name"],
                    username=u["username"],
                    email=u["email"],
                    code=u["code"],
                    qr_img=qr_base64
                )
                db.add(new_user)
                print(f"Created user: {u['name']} (Code: {u['code']})")
        db.commit()
        print("User seeding completed successfully!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding users: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_users()
