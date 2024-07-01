from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session
import json
import secrets
from typing import Dict
from passlib.context import CryptContext
from database import get_db, User, KeystrokeEvent

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
security = HTTPBasic()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

connections: Dict[str, WebSocket] = {}

class LoginForm(BaseModel):
    username: str
    password: str

def get_current_user(credentials: HTTPBasicCredentials = Depends(security), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == credentials.username).first()
    if not user or not pwd_context.verify(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return user

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(response: Response, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user or not pwd_context.verify(password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    session_token = secrets.token_urlsafe(16)
    response = RedirectResponse(url="/tracker", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="session_token", value=session_token)
    return response

@app.get("/tracker", response_class=HTMLResponse)
async def tracker(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse("index.html", {"request": request, "username": user.username})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    await websocket.accept()
    connections[user.username] = websocket

    try:
        while True:
            data = await websocket.receive_text()
            events = json.loads(data)

            for event in events:
                if 'event' in event:
                    if event['event'] == 'page_hidden':
                        print(f"User {user.username}: Page hidden at {event['timestamp']}")
                    elif event['event'] == 'page_visible':
                        print(f"User {user.username}: Page visible at {event['timestamp']}")
                else:
                    print(f"User {user.username}: {json.dumps(event, indent=2)}")
                    db_event = KeystrokeEvent(
                        user_id=user.id,
                        key=event['key'],
                        press_time=event['pressTime'],
                        release_time=event['releaseTime'],
                        hold_time=event['holdTime'],
                        flight_time=event['flightTime']
                    )
                    db.add(db_event)
                    db.commit()

            await websocket.send_text(f"Received {len(events)} events")
    except WebSocketDisconnect:
        del connections[user.username]
    finally:
        if user.username in connections:
            del connections[user.username]

@app.post("/create_user")
async def create_user(username: str, password: str, db: Session = Depends(get_db)):
    hashed_password = pwd_context.hash(password)
    new_user = User(username=username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    return {"message": "User created successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
