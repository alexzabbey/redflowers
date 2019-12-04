import asyncio
from fastai import *
from fastai.vision import *
from google.cloud import storage
import pickle
from uuid import uuid4
from databases import Database
from datetime import datetime

classes = ["calanit", "nurit", "pereg"]
path = Path(__file__).parent
BUCKET = "cnp-classifier-249308.appspot.com"
MODEL_FILE_NAME = "stage-2"
test = True


async def download_file(dest):
    client = storage.Client()
    bucket = client.get_bucket(BUCKET)
    blob = bucket.get_blob(f"model/{MODEL_FILE_NAME}.pth")
    if dest.exists():
        with open(path / "models/updated.json", "r") as j:
            file_updated = json.load(j)["updated"]
        if file_updated == str(blob.updated):
            print("whew, no need to download")
            return
    print("New model available! Downloading...")
    with open(dest, "wb") as f:
        blob.download_to_file(f)
    with open(path / "models/updated.json", "w") as fp:
        json.dump({"updated": str(blob.updated)}, fp)
    return


async def setup_learner():
    await download_file(path / "models" / f"{MODEL_FILE_NAME}.pth")
    data_bunch = ImageDataBunch.single_from_classes(
        path, classes, ds_tfms=get_transforms(), size=224
    ).normalize(imagenet_stats)
    learn = cnn_learner(data_bunch, models.resnet50, pretrained=False)
    learn.load(MODEL_FILE_NAME)
    with open(path / "models/learn.pkl", "wb") as p:
        pickle.dump(learn, p)
    return learn


async def write_metadata(payload):
    if test:
        with open("login.txt", "r") as f:
            os.environ["DATABASE_URL"] = f.read()
    DATABASE_URL = (
        os.environ["DATABASE_URL"].replace("postgres", "postgresql")
        + "?sslmode=require"
    )
    async with Database(DATABASE_URL) as database:
        if type(payload) == str:
            await database.execute(query=payload)
            return
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


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    tasks = [asyncio.ensure_future(setup_learner())]
    learn = loop.run_until_complete(asyncio.gather(*tasks))[0]
    loop.close()
