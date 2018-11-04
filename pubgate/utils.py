import binascii
import os
from typing import Any
from typing import List
from typing import Union


def make_label(activity):
    label = activity["type"]
    if isinstance(activity["object"], dict):
        label = f'{label}: {activity["object"]["type"]}'
    return label


def random_object_id() -> str:
    """Generates a random object ID."""
    return binascii.hexlify(os.urandom(8)).decode("utf-8")


def _to_list(data: Union[List[Any], Any]) -> List[Any]:
    """Helper to convert fields that can be either an object or a list of objects to a
    list of object."""
    if isinstance(data, list):
        return data
    return [data]


def check_obj_id(obj, user):
    if isinstance(obj, str):
        return obj.startswith(user.uri)
    elif isinstance(obj, dict):
        reply = obj.get("inReplyTo", "")
        undo_obj = obj.get("object", "")
        return obj["id"].startswith(user.uri) \
               or reply.startswith(user.uri) \
               or undo_obj.startswith(user.uri)
