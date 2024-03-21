import hashlib
import datetime
import ipaddress
import os
import json
import logging
from elasticsearch import AsyncElasticsearch, ConflictError, ConnectionError
from fastapi.logger import logger as fastapi_logger
from typing import Union

from fastapi import FastAPI, status, Header, Request, HTTPException, Response
from pydantic import BaseModel, ValidationError

app = FastAPI(title='FastAPI-Base',
              description='Base install of FastAPI.',
              version='1.0',
              )

verify_ssl_str = os.getenv('ELASTICSEARCH_VERIFY_SSL', 'True').strip('\"').lower()
verify_ssl = True

if verify_ssl_str.strip().lower() == 'false':
    verify_ssl = False

enable_debug_str = os.getenv('ENABLE_DEBUG', 'False').strip('\"').lower()
enable_debug = False

if enable_debug_str.strip().lower() == 'true':
    enable_debug = True

es = AsyncElasticsearch(
    os.getenv('ELASTICSEARCH_HOSTS'),
    verify_certs=verify_ssl,
    ssl_show_warn=False
)

# -----Logging Settings-----
# https://github.com/tiangolo/uvicorn-gunicorn-fastapi-docker/issues/19

gunicorn_error_logger = logging.getLogger("gunicorn.error")
gunicorn_logger = logging.getLogger("gunicorn")
uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_access_logger.handlers = gunicorn_error_logger.handlers

fastapi_logger.handlers = gunicorn_error_logger.handlers

if __name__ != "__main__":
    fastapi_logger.setLevel(gunicorn_logger.level)
else:
    fastapi_logger.setLevel(logging.DEBUG)
# -----Logging Settings-----

#  Close connection
# https://elasticsearch-py.readthedocs.io/en/7.9.1/async.html
@app.on_event("shutdown")
async def app_shutdown():
    await es.close()


# https://docs.pydantic.dev/latest/api/standard_library_types/#dict


class ClientData(BaseModel):
    ipv4address: ipaddress.IPv4Address
    data: dict
    created: datetime.datetime


@app.get("/")
async def read_root(request: Request,
                    x_forwarded_for: str = Header(None, alias='X-Forwarded-For'),
                    x_real_ip: str = Header(None, alias='X-Real-IP')):
    plz_send_ip = None
    try:
        plz_send_ip = request.headers.get('Plz-Send-IP')
    except TypeError:
        pass

    if enable_debug:
        uvicorn_access_logger.info("Request IP: " + request.client.host)
        uvicorn_access_logger.info("X-Forwarded_For IP: " + x_forwarded_for)
        uvicorn_access_logger.info("X-Real-IP: " + x_real_ip)
        if plz_send_ip is not None:
            uvicorn_access_logger.info("Plz-Send-IP: " + plz_send_ip)

    if plz_send_ip is not None:
        client_ip = plz_send_ip
    elif x_forwarded_for is not None:
        client_ip = x_forwarded_for
    elif x_real_ip is not None:
        client_ip = x_real_ip
    else:
        client_ip = request.client.host

    return {"ipv4address": client_ip}


@app.get("/fastapi-health")
async def get_health():
    return {"message": "alive"}


@app.get("/elastic-health")
async def get_health():
    try:
        return await es.cluster.health()
    except ConnectionError as e:
        return {"error": e.message}


# @app.get("/clientinfo/{ipaddress}", response_model=ClientData)
# async def get_client_by_ip(item_id: int, query: Union[str, None] = None):
#     return {"item_id": item_id, "query": query}

# Example test connection:
# https://www.slingacademy.com/article/ways-to-get-users-ip-address-in-fastapi/
# curl -d '{"clientname":"value1","data":"value2"}' \
#      -H "X-Forwarded-For: 192.168.0.10" \
#      -H "Content-Type: application/json" \
#      -X POST http://localhost:8081/clientinfo
@app.post("/clientinfo", status_code=status.HTTP_201_CREATED)
async def create_client_info_data(body: dict, request: Request,
                                  x_forwarded_for: str = Header(None, alias='X-Forwarded-For'),
                                  x_real_ip: str = Header(None, alias='X-Real-IP')):
    plz_send_ip = None
    try:
        plz_send_ip = request.headers.get('Plz-Send-IP')
    except TypeError:
        pass

    if enable_debug:
        uvicorn_access_logger.info("Request IP: " + request.client.host)
        uvicorn_access_logger.info("X-Forwarded_For IP: " + x_forwarded_for)
        uvicorn_access_logger.info("X-Real-IP: " + x_real_ip)
        if plz_send_ip is not None:
            uvicorn_access_logger.info("Plz-Send-IP: " + plz_send_ip)

    if plz_send_ip is not None:
        client_ip = plz_send_ip
    elif x_forwarded_for is not None:
        client_ip = x_forwarded_for
    elif x_real_ip is not None:
        client_ip = x_real_ip
    else:
        client_ip = request.client.host

    now = datetime.datetime.utcnow()
    # unix_now = now.timestamp()

    try:
        client_record = ClientData.model_validate({"ipv4address": client_ip, "data": body, "created": now})
    except ValidationError as error:
        raise HTTPException(
            status_code=400,
            detail={"message": "You have provided an invalid ip.", "error": error}
        )

    # Don't duplicate documents.  Create hash to track info
    raw_json = json.dumps({"ipv4address": client_ip, "data": body}, sort_keys=True)
    data_hash = hashlib.sha1(raw_json.encode())

    if enable_debug:
        uvicorn_access_logger.info(client_ip + ": " + raw_json)
        uvicorn_access_logger.info("SHA1 Hash: " + str(data_hash.hexdigest()))

    try:
        if not (await es.indices.exists(index="clientinfo")):
            await es.indices.create(index="clientinfo")
    except ConnectionError as e:
        return {"error": e.message}

    try:
        response = await es.create(
            index="clientinfo", id=data_hash.hexdigest(), body=client_record.model_dump_json(),
        )
        return {"hash": data_hash.hexdigest()}
    except ConflictError as e:
        return {"hash": data_hash.hexdigest(), "error": "document_exists"}
    # client_record.model_dump()
    # print(client_record.model_dump_json())

# @app.delete(f'/clientinfo/{sha1_hash}', status_code=status.HTTP_204_NO_CONTENT, responses_class=Response)
# async def remove_client_info_data(sha1_hash: str):
#     await es.delete(
#
#     )
