import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select

from database import Base, engine, get_db
from models import User, News, Task, AuctionLot, Bid, DutyReport
from security import hash_password, verify_password, make_session, read_session

ROOT = Path(__file__).resolve().parent
Base.metadata.create_all(bind=engine)
app = FastAPI(title="ЭРЭЛ", version="1.0.0")

COOKIE_NAME = "erel_session"

def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    uid = read_session(request.cookies.get(COOKIE_NAME))
    if not uid:
        raise HTTPException(status_code=401, detail="Требуется вход")
    user = db.get(User, uid)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Сессия недействительна")
    return user

def admin_only(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Только для администратора")
    return user

class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=80)

class LoginIn(BaseModel):
    username: str
    password: str

class NewsIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=5000)

class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=3000)
    due_date: Optional[str] = None

class LotIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=3000)
    starting_price: int = Field(ge=0, le=100000000)

class BidIn(BaseModel):
    amount: int = Field(gt=0, le=100000000)

class DutyIn(BaseModel):
    location: str = Field(min_length=1, max_length=120)
    note: str = Field(default="", max_length=2000)

@app.get("/")
def home():
    return FileResponse(ROOT / "index.html")

@app.get("/style.css")
def stylesheet():
    return FileResponse(ROOT / "style.css", media_type="text/css")

@app.get("/app.js")
def javascript():
    return FileResponse(ROOT / "app.js", media_type="application/javascript")

@app.get("/health")
def health():
    return {"status": "ok", "service": "ЭРЭЛ"}

@app.post("/api/register")
def register(data: RegisterIn, response: Response, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.username == data.username.strip().lower())):
        raise HTTPException(409, "Такой логин уже существует")
    count = db.query(User).count()
    user = User(username=data.username.strip().lower(),
                display_name=data.display_name.strip(),
                password_hash=hash_password(data.password),
                role="admin" if count == 0 else "student")
    db.add(user)
    db.commit()
    db.refresh(user)
    response.set_cookie(COOKIE_NAME, make_session(user.id), httponly=True,
                        secure=os.getenv("COOKIE_SECURE", "true").lower() == "true",
                        samesite="lax", max_age=60*60*24*7)
    return {"id": user.id, "username": user.username, "display_name": user.display_name, "role": user.role}

@app.post("/api/login")
def login(data: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == data.username.strip().lower()))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Неверный логин или пароль")
    response.set_cookie(COOKIE_NAME, make_session(user.id), httponly=True,
                        secure=os.getenv("COOKIE_SECURE", "true").lower() == "true",
                        samesite="lax", max_age=60*60*24*7)
    return {"id": user.id, "username": user.username, "display_name": user.display_name, "role": user.role}

@app.post("/api/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}

@app.get("/api/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "username": user.username, "display_name": user.display_name, "role": user.role}

@app.get("/api/news")
def news(db: Session = Depends(get_db), user: User = Depends(current_user)):
    items = db.scalars(select(News).order_by(News.created_at.desc()).limit(50)).all()
    return [{"id": x.id, "title": x.title, "body": x.body, "author": x.author_name,
             "created_at": x.created_at.isoformat()} for x in items]

@app.post("/api/news")
def add_news(data: NewsIn, db: Session = Depends(get_db), user: User = Depends(admin_only)):
    item = News(title=data.title, body=data.body, author_name=user.display_name)
    db.add(item); db.commit(); db.refresh(item)
    return {"id": item.id}

@app.get("/api/tasks")
def tasks(db: Session = Depends(get_db), user: User = Depends(current_user)):
    items = db.scalars(select(Task).order_by(Task.created_at.desc()).limit(100)).all()
    return [{"id": x.id, "title": x.title, "description": x.description,
             "due_date": x.due_date, "done": x.done} for x in items]

@app.post("/api/tasks")
def add_task(data: TaskIn, db: Session = Depends(get_db), user: User = Depends(admin_only)):
    item = Task(title=data.title, description=data.description, due_date=data.due_date)
    db.add(item); db.commit(); db.refresh(item)
    return {"id": item.id}

@app.post("/api/tasks/{task_id}/done")
def mark_task(task_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    item = db.get(Task, task_id)
    if not item: raise HTTPException(404, "Задание не найдено")
    item.done = True; db.commit()
    return {"ok": True}

@app.get("/api/auction")
def auction(db: Session = Depends(get_db), user: User = Depends(current_user)):
    lots = db.scalars(select(AuctionLot).order_by(AuctionLot.created_at.desc()).limit(50)).all()
    result = []
    for lot in lots:
        top = db.scalar(select(Bid.amount).where(Bid.lot_id == lot.id).order_by(Bid.amount.desc()).limit(1))
        result.append({"id": lot.id, "title": lot.title, "description": lot.description,
                       "starting_price": lot.starting_price, "current_bid": top or lot.starting_price})
    return result

@app.post("/api/auction")
def add_lot(data: LotIn, db: Session = Depends(get_db), user: User = Depends(admin_only)):
    lot = AuctionLot(title=data.title, description=data.description, starting_price=data.starting_price)
    db.add(lot); db.commit(); db.refresh(lot)
    return {"id": lot.id}

@app.post("/api/auction/{lot_id}/bid")
def bid(lot_id: int, data: BidIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    lot = db.get(AuctionLot, lot_id)
    if not lot: raise HTTPException(404, "Лот не найден")
    top = db.scalar(select(Bid.amount).where(Bid.lot_id == lot_id).order_by(Bid.amount.desc()).limit(1))
    minimum = top if top is not None else lot.starting_price
    if data.amount <= minimum: raise HTTPException(400, f"Ставка должна быть выше {minimum}")
    db.add(Bid(lot_id=lot_id, user_id=user.id, amount=data.amount))
    db.commit()
    return {"ok": True}

@app.get("/api/duties")
def duties(db: Session = Depends(get_db), user: User = Depends(current_user)):
    items = db.scalars(select(DutyReport).order_by(DutyReport.created_at.desc()).limit(100)).all()
    return [{"id": x.id, "location": x.location, "note": x.note,
             "author": x.author_name, "created_at": x.created_at.isoformat()} for x in items]

@app.post("/api/duties")
def add_duty(data: DutyIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    item = DutyReport(location=data.location, note=data.note, author_name=user.display_name)
    db.add(item); db.commit(); db.refresh(item)
    return {"id": item.id}
