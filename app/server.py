from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse, FileResponse
from starlette.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from starlette.background import BackgroundTasks, BackgroundTask
import uvicorn
from io import BytesIO
from uuid import uuid4
from databases import Database
from datetime import datetime
from fastai import *
from fastai.vision import *
from google.cloud import storage
import logging
import pickle

classes = ["calanit", "nurit", "pereg"]
path = Path(__file__).parent
BUCKET = "cnp-classifier-249308.appspot.com"
MODEL_FILE_NAME = "stage-2"

if not Path("keyfile.json").exists():
    with open("keyfile.json", "w") as fp:
        json.dump(json.loads(os.environ["KEYFILE"]), fp)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "keyfile.json"
client = storage.Client()
bucket = client.get_bucket(BUCKET)


async def download_file(dest):
    blob = bucket.get_blob(f"model/{MODEL_FILE_NAME}.pth")
    if dest.exists():
        with open(path / "models/updated.json", "r") as j:
            file_updated = json.load(j)["updated"]
        if file_updated == str(blob.updated):
            logging.info("Whew, no need to download")
            return False
    logging.info("New model available! Downloading...")
    with open(dest, "wb") as f:
        blob.download_to_file(f)
    with open(path / "models/updated.json", "w") as fp:
        json.dump({"updated": str(blob.updated)}, fp)
    return True


async def setup_learner():
    new_model = await download_file(path / "models" / f"{MODEL_FILE_NAME}.pth")
    if not new_model: return
    data_bunch = ImageDataBunch.single_from_classes(
        path, classes, ds_tfms=get_transforms(), size=224
    ).normalize(imagenet_stats)
    learn = cnn_learner(data_bunch, models.resnet50, pretrained=False)
    learn.load(MODEL_FILE_NAME)
    with open(path / "models/learn.pkl", "wb") as p:
        pickle.dump(learn, p)
    return


app = Starlette(on_startup=[setup_learner])
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_headers=["X-Requested-With", "Content-Type"],
)
app.mount("/static", StaticFiles(directory="app/static"))
test = False


async def store(f, filename):
    ext = filename.split(".")[1]
    content_type = f"image/{ext}" if ext != "jpg" else "image/jpeg"
    blob = bucket.blob(f"data/{filename}")
    blob.upload_from_file(f, content_type=content_type)


async def write_metadata(payload):
    if test:
        with open("login.txt", "r") as f:
            os.environ["DATABASE_URL"] = f.read()
    DATABASE_URL = (
        os.environ["DATABASE_URL"].replace("postgres", "postgresql")
        + "?sslmode=require"
    )
    async with Database(DATABASE_URL) as database:
        if payload.get("prediction", None):
            query = """INSERT INTO predictions(timestamp, filename, prediction, score)
                    VALUES (:timestamp, :filename, :prediction, :score)"""
            payload["timestamp"] = datetime.utcnow()
        elif payload.get("feedback", None):
            query = """UPDATE predictions
                    SET feedback=:feedback
                    WHERE filename=:filename"""
        else:
            return
        await database.execute(query=query, values=payload)


@app.route("/")
def index(request):
    global test
    test = True if request.client.host == "127.0.0.1" else False
    logging.info(f"running in test mode: {test}")
    html = path / "view" / "index.html"
    return HTMLResponse(html.open(encoding="utf-8").read())


@app.route("/analyze", methods=["POST"])
async def analyze(request):
    with open(path / "models/learn.pkl", "rb") as p:
        learn = pickle.load(p)
    data = await request.form()
    img_bytes = await data["file"].read()
    img = open_image(BytesIO(img_bytes))
    ext = data["file"].filename.split(".")[-1]
    filename = f"{str(uuid4())}.{ext}"
    prediction = learn.predict(img)
    score = prediction[2].data[prediction[1].item()].item()
    pred_str = str(prediction[0]) if score > 0.8 else "not red flower"
    res = {
        "filename": filename,
        "prediction": pred_str,
        "score": score,
    }
    tasks = BackgroundTasks()
    if not test:
        tasks.add_task(store, f=BytesIO(img_bytes), filename=filename)
        tasks.add_task(write_metadata, payload=res)
    # TODO: add score
    return JSONResponse(res, background=tasks)


@app.route("/feedback", methods=["POST"])
async def feedback(request):
    req = await request.json()
    print(req)
    if not test:
        task = BackgroundTask(write_metadata, payload=req)
        return JSONResponse("thx", background=task)
    else:
        return JSONResponse("thx")
