from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.wsgi import WSGIMiddleware
import os
from dotenv import load_dotenv
import httpx
import pandas as pd

# Load environment variables
load_dotenv()  # take environment variables from .env.
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# Initialize FastAPI app
app = FastAPI()

# Set up Jinja2 for templating
templates = Jinja2Templates(directory="templates")

# Mount the static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# TMDb Client
class TMDbClient:
    BASE_URL = "https://api.themoviedb.org/3"
    
    def __init__(self, api_key):
        self.api_key = api_key
        
    def get_movie(self, movie_id):
        url = f"{self.BASE_URL}/movie/{movie_id}"
        params = {"api_key": self.api_key}
        response = httpx.get(url, params=params)
        return response.json()
    
    def search_movies(self, query):
        url = f"{self.BASE_URL}/search/movie"
        params = {"api_key": self.api_key, "query": query}
        response = httpx.get(url, params=params)
        return response.json()

tmdb_client = TMDbClient(TMDB_API_KEY)

# Load the dataset
ratings = pd.read_csv('movies.csv')

def recommend_movies(user_id, n_recommendations=5):
    user_ratings = ratings[ratings['userId'] == user_id]
    similar_users = ratings[~ratings['userId'].isin(user_ratings['userId'])]
    similar_users = similar_users.groupby('movieId').agg({'rating':'mean'})
    similar_users = similar_users.sort_values('rating', ascending=False).head(n_recommendations)
    return similar_users.index.tolist()

# Routes
@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/movies/search")
def search_movies(request: Request, query: str):
    search_results = tmdb_client.search_movies(query)
    movies = search_results.get('results', [])
    return templates.TemplateResponse("results.html", {"request": request, "movies": movies})

@app.get("/recommendations/{user_id}")
def get_user_recommendations(user_id: int):
    recommendations = recommend_movies(user_id)
    return {"recommendations": recommendations}

@app.get("/recommendations/movie/{movie_id}")
def get_movie_recommendations(movie_id: int):
    similar_movies = tmdb_client.get_movie(movie_id).get('similar', {}).get('results', [])
    return {"recommendations": [movie['title'] for movie in similar_movies]}

# Create WSGI application for deployment
application = WSGIMiddleware(app)
