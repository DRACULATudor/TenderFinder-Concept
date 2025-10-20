import os
from dotenv import load_dotenv, find_dotenv
from fastapi import APIRouter, HTTPException
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import credentials
from typing import Annotated
from firebase_admin.auth import verify_id_token

_ = load_dotenv(find_dotenv())

cred_path = os.getenv("PATH_TO_FIREBASE")


cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)


# This tells FastAPI: "I'm expecting an 'Authorization' header
# with a 'Bearer' token in it."
bearer_token = HTTPBearer(auto_error=False)
#Think of it like a key – whoever holds the key (the bearer token) can unlock the door (access the resource)


"""(get_fb_user_base_on_token)
Uses bearer token to identify firebase user id
Args:
    token : the bearer token. Can be None as we set auto_error to False
Returns:
    dict: the firebase user on success
Raises:
    HTTPException 401 if user does not exist or token is invalid
    """
def get_fb_user_base_on_token(
        token: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_token)]
        )->dict | None:
    try:
        if token is None:
            raise ValueError("Invalid/Incorect Token !")
        user = verify_id_token(token.credentials)
        return user
        #if everything foes right w the verification it will reutrn the payload(users data)
    
    except Exception:
        #else we raise exception
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    
