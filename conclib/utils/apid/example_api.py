from fastapi import FastAPI

app = FastAPI()


@app.get("/healthz")
def get_healthcheck():
    """ Basic healthcheck """
    return {"status": "ok"}

