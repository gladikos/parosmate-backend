# auth.py
from fastapi import Request, APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from models import Base, User, Itinerary, FavoritePlace, get_db, engine

SECRET_KEY = "supersecretkey"  # Replace later with env var
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

Base.metadata.create_all(bind=engine)

class UserCreate(BaseModel):
    name: str
    surname: str
    mobile: str
    email: str
    password: str

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=30))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = get_password_hash(user.password)
    db_user = User(
        name=user.name,
        surname=user.surname,
        mobile=user.mobile,
        email=user.email,
        hashed_password=hashed
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"message": "User created successfully"}

@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(data={"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

@router.get("/me")
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {
            "id": user.id,
            "name": user.name,
            "surname": user.surname,
            "mobile": user.mobile,
            "email": user.email,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/save-itinerary")
def save_itinerary(itinerary: dict, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    new_itinerary = Itinerary(
        user_id=user.id,
        days=itinerary["days"],
        adults=itinerary["adults"],
        children=itinerary["children"],
        transportation=itinerary["transportation"],
        age_range=itinerary["ageRange"],
        budget=itinerary["budget"],
        priorities=itinerary["priorities"],
        content=itinerary["content"]
    )
    db.add(new_itinerary)
    db.commit()
    return {"message": "Itinerary saved"}

@router.get("/user/itineraries")
def get_user_itineraries(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    itineraries = db.query(Itinerary).filter(Itinerary.user_id == user.id).all()
    return [
        {
            "id": it.id,
            "days": it.days,
            "adults": it.adults,
            "children": it.children,
            "transportation": it.transportation,
            "ageRange": it.age_range,
            "budget": it.budget,
            "priorities": it.priorities,
            "content": it.content,
            "createdAt": it.created_at.isoformat()
        }
        for it in itineraries
    ]

@router.delete("/itineraries/{itinerary_id}")
def delete_itinerary(
    itinerary_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    itinerary = db.query(Itinerary).filter(
        Itinerary.id == itinerary_id,
        Itinerary.user_id == current_user["id"]
    ).first()

    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")

    db.delete(itinerary)
    db.commit()
    return {"detail": "Itinerary deleted successfully"}

@router.post("/save-favorite")
async def save_favorite(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    data = await request.json()
    new_fav = FavoritePlace(
        user_id=user["id"],
        name=data["name"],
        description=data["description"],
        latitude=data["latitude"],
        longitude=data["longitude"],
    )
    db.add(new_fav)
    db.commit()
    db.refresh(new_fav)
    return {"message": "Favorite saved"}

@router.get("/user/favorites")
def get_favorites(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(FavoritePlace).filter_by(user_id=user["id"]).order_by(FavoritePlace.created_at.desc()).all()

@router.delete("/favorites/{fav_id}")
def delete_favorite(fav_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    fav = db.query(FavoritePlace).filter_by(id=fav_id, user_id=user["id"]).first()
    if fav:
        db.delete(fav)
        db.commit()
        return {"message": "Favorite deleted"}
    raise HTTPException(status_code=404, detail="Not found")
